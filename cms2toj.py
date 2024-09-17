import argparse
import json
import logging
import os
import re
import asyncio
from function import *

async def main():
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
        print('-' * 70)
        print('請選擇競賽ID')
        print('ID\tName')
        for idx in contestids:
            print('{}\t{}'.format(idx, data[idx]['description']))
        idx = input('選擇>')
        if idx in contestids:
            contest = data[idx]

    print('-' * 70)
    print('正在處理 {}'.format(contest['description']))
    print(contest)

    compress_tasks = []
    for taskid in contest['tasks']:
        task = data[taskid]
        print('-' * 70)
        print(taskid, task['name'], task['title'])

        taskpath = os.path.join(outputpath, taskid)
        makedirs(taskpath)

        # res/testdata / testcases
        makedirs(taskpath, 'res/testdata')

        datasetid = task['active_dataset']
        dataset = data[datasetid]

        datacasemap = {}
        offset = 1
        logging.info('Copying {} testdatas'.format(len(dataset['testcases'])))
        for filename in dataset['testcases']:
            testcaseid = dataset['testcases'][filename]
            testcase = data[testcaseid]
            datacasemap[testcase['codename']] = offset
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
        if isinstance(dataset['score_type_parameters'][0][1], int):
            # Case 1. See https://cms.readthedocs.io/en/v1.4/Score%20types.html#groupmin
            offset = 1
            for score in dataset['score_type_parameters']:
                conf['test'].append({
                    'data': list(range(offset, offset + score[1])),
                    'weight': score[0]
                })
                offset += score[1]
        elif isinstance(dataset['score_type_parameters'][0][1], str):
            # Case 2.
            for score in dataset['score_type_parameters']:
                test = {
                    'data': [],
                    'weight': score[0]
                }
                for codename in datacasemap:
                    if re.match(score[1], codename):
                        test['data'].append(datacasemap[codename])
                conf['test'].append(test)
        else:
            raise Exception('Bad score_type_parameters type: {}'.format(dataset['score_type_parameters']))

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
        async def _compress_task(taskpath, outputpath, taskid, task_name, task_title):
            returncode = await run_and_wait_process('tar', *[
                '-C',
                taskpath,
                '-cJf',
                os.path.join(outputpath, '{}.tar.xz'.format(taskid)),
                'http',
                'res',
                'conf.json'
            ])
            if returncode != 0:
                logging.info('{} {} {} Compress failed'.format(taskid, task_name, task_title))
            else:
                logging.info('{} {} {} Compress finished'.format(taskid, task_name, task_title))

        compress_tasks.append(_compress_task(taskpath, outputpath, taskid, task['name'], task['title']))

    logging.info('Starting compress')
    await asyncio.gather(*compress_tasks)

if __name__ == '__main__':
    import sys
    if sys.version_info.minor >= 7:
        asyncio.run(main())
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
