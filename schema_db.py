#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# schema.py: definition for the cache database
# This little script initializes the cache database.

import os, sqlite3

def schemaDb():
    if os.path.isfile('config.py'):
        # DB path already configured
        from config import CFG_CACHEDBPATH
        dbPath = CFG_CACHEDBPATH
    else:
        # We use the default DB path
        dbPath = 'files/cache/taskgrader-cache.sqlite'

    db = sqlite3.connect(dbPath)
    db.execute("""CREATE TABLE IF NOT EXISTS cache
    (id INTEGER PRIMARY KEY,
     filesid TEXT,
     hashlist TEXT)""")

if __name__ == '__main__':
    schemaDb()
