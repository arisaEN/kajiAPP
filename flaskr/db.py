import sqlite3
DATABASE='database.db'
#明細
def create_works_table():
    con=sqlite3.connect('database.db')
    con.execute("CREATE TABLE IF NOT EXISTS works(id INTEGER PRIMARY KEY AUTOINCREMENT, day date, name TEXT,work_id INTEGER, work TEXT, percent TEXT)")

    con.close()

#家事リスト
def create_workList_table():
    con=sqlite3.connect('database.db')
    con.execute("CREATE TABLE IF NOT EXISTS workList(work_id INTEGER PRIMARY KEY AUTOINCREMENT, workName text, workNamePoint text,家事分類区分番号 INTEGER)")

    con.close()
#オペレーター名前リスト
def create_nameList_table():
    con=sqlite3.connect('database.db')
    con.execute("CREATE TABLE IF NOT EXISTS nameList(name_id INTEGER PRIMARY KEY AUTOINCREMENT, name text)")

    con.close()

#家事分類区分
def create_家事分類区分_table():
    con=sqlite3.connect('database.db')
    con.execute("CREATE TABLE IF NOT EXISTS 家事分類区分(家事分類区分番号ID INTEGER PRIMARY KEY AUTOINCREMENT, 区分番号 INTEGER, 区分名 varchar(40))")

    con.close()
