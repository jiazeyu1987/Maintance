"""Spug local manual task: live query, readable output, nonzero on failure."""
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request


def main():
    config = json.loads(Path('/run/intruoyi-spug/runtime-versions.private.json').read_text())
    request = urllib.request.Request('http://host.docker.internal:18086/versions',
                                     headers={'Authorization': 'Bearer ' + config['token']})
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        result = json.load(error)
    except (urllib.error.URLError, TimeoutError):
        print('查询失败：本机版本查询服务不可达，未使用旧记录代替实时结果。')
        return 1
    print('三服 IntRuoyi 当前版本（实时只读查询）')
    for row in result.get('servers', []):
        if 'error' in row:
            print('{} {}：查询失败 {}'.format(row['name'], row['host'], row['error']))
        else:
            print('{} {}：前端 {}；后端 {}；MySQL {}'.format(
                row['name'], row['host'], row['components']['frontend']['versionName'],
                row['components']['backend']['versionName'], row['mysqlVersion']))
    if result.get('allSucceeded'):
        print('镜像比较：' + ('三服前端、后端、数据库镜像全部一致' if all(result['sameImages'].values()) else '存在版本差异，详见下方'))
    print('\n以下为逐服详细结果，可向下滚动查看。')
    for row in result.get('servers', []):
        print('\n【{} {}】'.format(row['name'], row['host']))
        if 'error' in row:
            print('查询失败：' + row['error'])
            continue
        print('访问入口：' + row['entryUrl'])
        print('查询时间：' + row['observedAt'])
        for role, label in [('frontend', '前端'), ('backend', '后端'), ('database', '数据库镜像')]:
            c = row['components'][role]
            print('{}：{}；状态：{}'.format(label, c['versionName'], c['state']))
            print('  镜像：' + c['image'])
            print('  摘要：' + c['imageId'])
            print('  实例：' + c['container'])
        print('MySQL：{}；业务库：{}；表/视图：{}'.format(row['mysqlVersion'], row['database'], row['tableCount']))
    print('\n三服镜像一致性：' + json.dumps(result.get('sameImages', {}), ensure_ascii=False))
    for role, label in [('frontend', '前端'), ('backend', '后端'), ('database', '数据库镜像')]:
        equal = result.get('sameImages', {}).get(role)
        print('{}：{}'.format(label, '三服一致' if equal else '存在差异或查询不完整，请查看各服结果'))
    print(result.get('note', result.get('error', '')))
    return 0 if result.get('allSucceeded') else 1


if __name__ == '__main__':
    sys.exit(main())
