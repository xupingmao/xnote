# encoding=utf-8
# Created by xupingmao on 2017/04/16

import web.db as db

import config

def get_file_db():
    return db.SqliteDB(db=config.DB_PATH)