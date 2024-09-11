from flaskr import app
from flask import render_template,request,redirect,url_for
import sqlite3
import datetime
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
        datetime=datetime,
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


