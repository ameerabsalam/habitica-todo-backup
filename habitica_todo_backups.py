# Free habitica accounts deleted compelted todos after 30 days
# This script will extract todos in a nice way and store in a master DB (file DB on disk)

from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware

import json
import argparse
import sys
import os
import shutil
from datetime import datetime
from typing import Dict, List


def _setup_command_line_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-f','--file-path', help='Path to Habitica user data JSON', required=True)
    #TODO: Add search/view feature on file? see https://github.com/patarapolw/tinydb-viewer
    args = parser.parse_args()
    return args

def _process_checklist(checklist=[]) -> List[str]:
    items = []
    for item in checklist:
        items.append(item.get('text'))
    return items

def _extract_completed_todos(file_path: str) -> List[Dict]:

    todos = []
    with open(file_path) as json_file:
        print('Loading JSON file...')
        data = json.load(json_file)
        todo_list = data.get('tasks', {}).get('todos')
        for todo in todo_list:
            if todo.get('completed'):
                todos.append({
                    'id': todo.get('_id'),
                    'title': todo.get('text'),
                    'notes': todo.get('notes'),
                    'checklist': _process_checklist(todo.get('checklist')),
                    'date_completed': todo.get('dateCompleted')
                })

    print(f'{len(todos)} completed todos extracted from input file')
    from pprint import pprint
    # pprint(todos[1])
    return todos

def _backup_db():
    DB_BACKUP_DIR = '.database_backups'
    DB_PATH = 'full_history_db.json'
    try:
        os.mkdir(DB_BACKUP_DIR)
    except FileExistsError:
        pass
    try:
        shutil.copy(DB_PATH, DB_BACKUP_DIR)
    except FileNotFoundError:
        return
    backup_filename = (str(datetime.now())).replace(' ', '_') + '.json'
    shutil.move(DB_BACKUP_DIR + '/' + DB_PATH, DB_BACKUP_DIR + '/' + backup_filename)
    print(f'Backed up database to {DB_BACKUP_DIR + "/" + backup_filename}')

def _save_to_db(todos: List[Dict]):

    #TODO: backup existing to hidden backups folder using abs time as fname
    _backup_db()

    db = TinyDB('full_history_db.json', sort_keys=True, indent=4, separators=(',', ': '), storage=CachingMiddleware(JSONStorage))
    print(f'{len(db.all())} currently in database')

    query = Query() # should this be initialized in loop?
    # after insertion, will next db.count/search get updated results?
    # 'TinyDB caches query result for performance. That way re-running a query won’t have to read the data from the storage as long as the database hasn’t been modified.'

    # check for duplicates
    for todo in todos:
        # not gauranteed that Habitica doesn't re-use ids after todo deleted from server
        # thus more complex condition to check for duplicate
        duplicates_count = db.count(
            (query.id == todo.get('id')) &
            (query.title == todo.get('title')) &
            (query.date_completed == todo.get('date_completed'))
        )
        if duplicates_count > 0:
            print(f'Duplicate encoutered!  A todo in input file matches {duplicates_count} todo(s) in database (matches id, name and completed date)')
            print('Skipping insertion.  Please verify that this behavior is correct')
            print(f'Culprint todo (input file):\n{todo}')
            print('Exiting ...')
            sys.exit()

    inserted = db.insert_multiple(todos)
    print(f'Inserted {len(inserted)} todos :)')
    # close for safety due to caching middleware
    db.close()

def main():
    args = _setup_command_line_arguments()
    file_path = vars(args).get('file_path')
    todos = _extract_completed_todos(file_path)
    # TODO: prettified DB json file? https://tinydb.readthedocs.io/en/latest/usage.html#storage-types
    _save_to_db(todos)

if __name__ == '__main__':
    main()
