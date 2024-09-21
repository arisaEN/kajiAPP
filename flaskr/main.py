from flaskr import app
from flask import render_template,request,redirect,url_for
import sqlite3
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

DATABASE ='database.db'

#ページにアクセスした時
@app.route('/')
def index():
    workList = get_works()
    nameList = request.cookies.get('nameList', default=get_names())
    con = sqlite3.connect(DATABASE)
    #昨日と今日の実績
    db_works = con.execute("SELECT id,day,name,work,percent FROM works where day BETWEEN DATE('now', '-1 day') AND DATE('now')  ORDER BY id desc LIMIT 15").fetchall()
    #今月の集計結果
    db_result = con.execute("""
    SELECT works.name, 
       SUM(workList.workNamePoint * (works.percent * 0.01)) AS total_points, 
       CAST(SUM(workList.workNamePoint * (works.percent * 0.01)) / 
            (SELECT SUM(workList.workNamePoint * (works.percent * 0.01)) 
             FROM works 
             JOIN workList ON works.work_id = workList.work_id
             WHERE strftime('%Y-%m', works.day) = strftime('%Y-%m', 'now')) * 100 AS INTEGER) AS percentage 
    FROM works 
    JOIN workList ON works.work_id = workList.work_id 
    WHERE strftime('%Y-%m', works.day) = strftime('%Y-%m', 'now')
    GROUP BY works.name
    ORDER BY total_points DESC;
    """).fetchall()
    ##折れ線グラフ用データ取得
    query = """
    SELECT 
        works.name, 
        works.day, 
        SUM(workList.workNamePoint * (works.percent * 0.01)) AS total_points
    FROM 
        works 
    JOIN 
        workList 
    ON 
        works.work_id = workList.work_id 
    WHERE 
        works.day BETWEEN DATE('now', '-2 month') AND DATE('now')
    GROUP BY 
        works.name, works.day
    ORDER BY 
        works.day, works.name;
    """
    df = pd.read_sql_query(query, con)

    # 家事分類区分のデータ取得
    con = sqlite3.connect(DATABASE)
    db_category_result = con.execute("""
        SELECT works.name, 家事分類区分.区分名,
               SUM(workList.workNamePoint * (works.percent * 0.01)) AS total_points
        FROM works 
        JOIN workList ON works.work_id = workList.work_id 
        JOIN 家事分類区分 ON workList.家事分類区分番号 = 家事分類区分.家事分類区分ID
        WHERE strftime('%Y-%m', works.day) = strftime('%Y-%m', 'now')
        GROUP BY works.name, 家事分類区分.区分名
        ORDER BY works.name, 家事分類区分.区分名;
    """).fetchall()
    con.close()

    # 円グラフ用データの準備
    category_data = []
    for row in db_category_result:
        category_data.append({'name': row[0], 'category': row[1], 'total_points': row[2]})


    con.close()
    works = []
    analysisResults = []
    
    for row in db_works:
        works.append({'id': row[0], 'day': row[1], 'name': row[2], 'work': row[3], 'percent': row[4]})
    for row in db_result:
        analysisResults.append({'name': row[0], 'total_points': row[1],'percentage': row[2] })
    
    # 日付を日付型に変換
    df['day'] = pd.to_datetime(df['day'])
    
    # データをピボットテーブルに変換
    pivot_df = df.pivot(index='day', columns='name', values='total_points').fillna(0)
    
    # データをHTMLに渡すための準備
    dates = pivot_df.index.strftime('%Y-%m-%d').tolist()
    data = pivot_df.to_dict(orient='list')
    
    return render_template(
        'index.html',
        works=works,
        workList=workList,
        nameList=nameList,
        analysisResults=analysisResults,
        # datetimeをdatetimeモジュールから直接渡す
        current_datetime=datetime.now(),  # 変更点
        dates=dates, data=data,
        category_data=category_data
    )


def get_data_from_db(query):
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@app.route('/option')
def option():
    con = sqlite3.connect(DATABASE)
    db_workList = con.execute('SELECT * FROM workList ORDER BY work_id desc').fetchall()
    con.close()
    workList = []
    for row in db_workList:
        workList.append({'id': row[0], 'workName': row[1], 'workNamePoint': row[2],'家事分類区分番号': row[3]})

    con = sqlite3.connect(DATABASE)
    db_nameList = con.execute('SELECT * FROM nameList ORDER BY name_id desc').fetchall()
    con.close()
    nameList = []
    for row in db_nameList:
        nameList.append({'id': row[0], 'name': row[1]})


    

    return render_template(
        'option.html',
        workList=workList,
        nameList=nameList
        
    )

@app.route('/scr')
def scr():
  
    return render_template(
        'scr.html',

        
    )
###################################################################
@app.route('/eat')
def eat():
    # 今年の今月のレコードが存在しなければ挿入

    insert_eat_record_if_not_exists()
    if has_eat_details():  # eat_detail が存在するかチェック
        update_eat_amount()  # 存在する場合のみ update 関数を呼び出す
    
    records = get_eat_records()

    # 各レコードの明細を取得
    details = { (record[0], record[1]): get_eat_detail_records(record[0], record[1]) for record in records }

    return render_template(
        'eat.html',
        records=records,
        details=details  # 明細を渡す
    )


def has_eat_details():
    # SQLite3 を使って eat_detail テーブルのレコード数を確認する
    con = sqlite3.connect('database.db')  # データベースに接続
    cur = con.cursor()  # カーソルを作成

    # SQLクエリでレコード数を取得
    cur.execute("SELECT COUNT(*) FROM eat_detail")
    count = cur.fetchone()[0]  # 結果からレコード数を取得

    con.close()  # データベース接続を閉じる

    return count > 0  # レコードが1件以上あればTrue




# テーブル作成・データ挿入関数
def insert_eat_record_if_not_exists():
    con = sqlite3.connect('database.db')
    cur = con.cursor()

    # テーブルが存在しない場合の作成
    cur.execute("""
        CREATE TABLE IF NOT EXISTS eat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER,
            month INTEGER,
            amount REAL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 現在の年と月を取得し、月は"00"という書式にする
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # 月を"00"という書式にする
    formatted_month = str(current_month).zfill(2)

    # 今年の今月のレコードが存在するか確認
    cur.execute("""
        SELECT 1 FROM eat WHERE year = ? AND month = ?
    """, (current_year, formatted_month))
    
    record_exists = cur.fetchone()

    # レコードが存在しなければ新規作成
    if not record_exists:
        cur.execute("""
            INSERT INTO eat (year, month, amount, description)
            VALUES (?, ?, ?, ?)
        """, (current_year, formatted_month, 0.0, '初期レコード'))



    con.commit()
    con.close()

# テーブルのデータを取得してHTMLに表示する関数
def get_eat_records():
    con = sqlite3.connect('database.db')
    cur = con.cursor()

    # `created_at` の降順で12件取得
    cur.execute("""
        SELECT year, month, amount, description, created_at
        FROM eat
        ORDER BY created_at DESC
        LIMIT 12
    """)
    records = cur.fetchall()
    con.close()

    return records


def update_eat_amount():
    conn = sqlite3.connect('database.db')  # データベース接続
    cursor = conn.cursor()

    # SQL実行
    cursor.execute('''
        UPDATE eat
        SET amount = (
            SELECT SUM(ed.amount)
            FROM eat_detail ed
            WHERE ed.year = eat.year AND ed.month = eat.month
        )
        WHERE EXISTS (
            SELECT 1
            FROM eat_detail ed
            WHERE ed.year = eat.year AND ed.month = eat.month
        );
    ''')

    conn.commit()  # 変更をコミット
    conn.close()   # 接続を閉じる

# 新しい関数を追加
def get_eat_detail_records(year, month):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("""
        SELECT id, amount, input_time  
        FROM eat_detail
        WHERE year = ? AND month = ?
    """, (year, month))
    records = cur.fetchall()
    con.close()
    return records



@app.route('/update_detail', methods=['POST'])
def update_detail():
    detail_id = request.form['id']
    amount = request.form['amount']

    con = sqlite3.connect(DATABASE)
    con.execute("""
        UPDATE eat_detail
        SET amount = ?
        WHERE id = ?
    """, (amount, detail_id))
    
    con.commit()
    con.close()
    
    return redirect(url_for('eat'))  # 食費記録ページにリダイレクト


    
##################################################################
#食費明細
@app.route('/save_detail', methods=['POST'])
def save_detail():
    year = request.form['year']
    month = request.form['month']
    amount = request.form['amount']

    con = sqlite3.connect(DATABASE)
    con.execute("""
        INSERT INTO eat_detail (year, month, amount)
        VALUES (?, ?, ?)
    """, (year, month, amount))
    
    con.commit()
    con.close()
    
    return redirect(url_for('eat'))  # 食費記録ページにリダイレクト



#家事実績テーブル
@app.route('/register',methods=['post'])
def register():

    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    cursor.execute('SELECT MAX(id) FROM works')
    max_id = cursor.fetchone()[0]
    if max_id is None:
        new_id = 1
    else:
        new_id = max_id + 1
    con.close()
    id = new_id
    day = request.form['day']
    name = request.form['name']
    work_id = request.form['workId']
    work = request.form['workName']
    percent = request.form['percent']

    con = sqlite3.connect(DATABASE)
    con.execute('INSERT INTO works VALUES(?,?,?,?,?,?)',
               [id,day,name,work_id,work,percent] )
    
    con.commit()
    con.close()
    response = redirect(url_for('index'))
    response.set_cookie('name', name, max_age=31536000)  # 1年の有効期間
    return response


#家事リストの挿入
@app.route('/register2',methods=['post'])
def register2():

    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    cursor.execute('SELECT MAX(work_id) FROM workList')
    max_id = cursor.fetchone()[0]
    if max_id is None:
        new_id = 1
    else:
        new_id = max_id + 1

    con.close()
    work_id=new_id
    workName=request.form['workName']
    workNamePoint=request.form['workNamePoint']
    家事分類区分番号=request.form['家事分類区分番号']
    con = sqlite3.connect(DATABASE)
    con.execute('INSERT INTO workList VALUES(?,?,?,?)',
               [work_id,workName,workNamePoint,家事分類区分番号] )
    
    con.commit()
    con.close()
    return redirect(url_for('option'))


#名前リストの挿入
@app.route('/register3',methods=['post'])
def register3():

    con = sqlite3.connect(DATABASE)
    cursor = con.cursor()
    cursor.execute('SELECT MAX(name_id) FROM nameList')
    max_id = cursor.fetchone()[0]
    if max_id is None:
        new_id = 1
    else:
        new_id = max_id + 1
    con.close()
    name_id=new_id
    name=request.form['name']
    con = sqlite3.connect(DATABASE)
    con.execute('INSERT INTO nameList VALUES(?,?)',
               [name_id,name] )
    con.commit()
    con.close()
    return redirect(url_for('option'))






def get_works():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT work_id, workName,workNamePoint,家事分類区分番号 FROM workList")
    works = cursor.fetchall()
    conn.close()
    return [(work[0], work[1],work[2],work[3]) for work in works]

def get_names():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM nameList")
    names = cursor.fetchall()
    conn.close()
    
    return [name[0] for name in names]





if __name__ == '__main__' :
    app.run(debug=False ,host='0.0.0.0',port=8888)
    #app.run(debug=False ,host='100.64.16.21',port=80)






