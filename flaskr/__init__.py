#初期化処理を書く

from flask import Flask

app = Flask(__name__)
import flaskr.main

from flaskr import db
db.create_works_table()
db.create_workList_table()
db.create_nameList_table()
db.create_家事分類区分_table()




