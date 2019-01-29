import argparse
import os
import json
import logging
import subprocess
from function import *


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

parser = argparse.ArgumentParser(description='cms2toj')
parser.add_argument('inputpath', type=str,
                    help='使用cmsDumpExporter產出的路徑，不支援壓縮檔')
parser.add_argument('outputpath', type=str, help='輸出的資料夾')
args = parser.parse_args()
inputpath = args.inputpath
outputpath = args.outputpath

with open(os.path.join(inputpath, 'contest.json')) as f:
    data = json.load(f)

contestids = []
for idx in data:
    if type(data[idx]) is not dict:
        continue
    if data[idx]['_class'] == 'Contest':
        contestids.append(idx)

contest = None
while contest is None:
    print('-'*70)
    print('請選擇競賽ID')
    print('ID\tName')
    for idx in contestids:
        print('{}\t{}'.format(idx, data[idx]['description']))
    idx = input('選擇>')
    if idx in contestids:
        contest = data[idx]

print('-'*70)
print('正在處理 {}'.format(contest['description']))
print(contest)
for taskid in contest['tasks']:
    task = data[taskid]
    print('-'*70)
    print(taskid, task['name'], task['title'])

    taskpath = os.path.join(outputpath, taskid)
    makedirs(taskpath)

    # res/testdata / testcases
    makedirs(taskpath, 'res/testdata')

    datasetid = task['active_dataset']
    dataset = data[datasetid]

    offset = 1
    logging.info('Copying {} testdatas'.format(len(dataset['testcases'])))
    for filename in dataset['testcases']:
        testcaseid = dataset['testcases'][filename]
        testcase = data[testcaseid]
        copyfile(
            (inputpath, 'files', testcase['input']),
            (taskpath, 'res/testdata', '{}.in'.format(offset))
        )
        copyfile(
            (inputpath, 'files', testcase['output']),
            (taskpath, 'res/testdata', '{}.out'.format(offset))
        )
        offset += 1

    # conf
    conf = {
        'timelimit': 0,
        'memlimit': 0,
        'compile': 'g++',
        'score': 'rate',
        'check': 'diff',
        'test': [],
        'metadata': {},
    }
    conf['timelimit'] = int(dataset['time_limit'] * 1000)
    conf['memlimit'] = int(dataset['memory_limit'] * 1024)
    offset = 1
    for score in dataset['score_type_parameters']:
        conf['test'].append({
            'data': list(range(offset, offset + score[1])),
            'weight': score[0]
            })
        offset += score[1]
    logging.info('Creating config file')
    with open(os.path.join(taskpath, 'conf.json'), 'w') as conffile:
        json.dump(conf, conffile, indent=4)

    # http / statements
    makedirs(taskpath, 'http')

    statements = task['statements']
    if len(statements) == 0:
        logging.info('No statements')
        statement = None
    else:
        statementid = list(statements.values())[0]
        statement = data[statementid]
        logging.info('Copying statements')
        copyfile(
            (inputpath, 'files', statement['digest']),
            (taskpath, 'http', 'cont.pdf')
        )

    p = subprocess.Popen([
        'tar',
        '-C',
        taskpath,
        '-cJf',
        os.path.join(outputpath, '{}.tar.xz'.format(taskid)),
        'http',
        'res',
        'conf.json'
    ])
