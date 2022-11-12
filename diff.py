import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--projects-regex', default='SP.*')
args = parser.parse_args()

from datetime import datetime, timedelta
import humanize
import pymongo
from bson.objectid import ObjectId

client = pymongo.MongoClient('172.18.0.3', 27017)
db = client.sharelatex

def date2str(date):
    #return date.strftime('%Y-%m-%d %H:%M')
    return humanize.naturaltime(date)

def get_user(user_id):
    user = db.users.find_one({'_id': ObjectId(user_id)})
    return user['email'] if user else 'unknown'

def find_filename(folders, doc_id):
    for folder in folders:
        if 'docs' in folder:
            for doc in folder['docs']:
                if doc['_id'] == doc_id:
                    return doc['name']
        if 'folders' in folder:
            ret = find_filename(folder['folders'], doc_id)
            if ret: return ret

print('<html>')
print('<head>')
print('<title>THEIA SP Track Changes</title>')
print('<meta charset="UTF-8">')
print('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
print('<style>.highlight {background-color: #FFFF00}</style>')
print('</head>')
print('<body>')
print('<h1>THEIA SP Track Changes</h1>')

print('<p>Notice: &bull; Only the last 30 day changes are displayed. &bull; This information is updated every 5 minutes. &bull; Last 48h of changes are in <span class="highlight">highlight</span>.</p>')
print(f'<p>Last track changes update: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>')
ago30days = datetime.now() - timedelta(days=30)
recent = datetime.now() - timedelta(hours=48)

projects = db.projects.find({'name': {'$regex': args.projects_regex}}).sort('lastUpdated', pymongo.DESCENDING)
projects = list(projects)

print("<h2>SP Index (ordered by last update)</h2>")
print('<table border="1">')
print('<tr><th>Document</th><th>Last update</th><th>Updated by</th></tr>')
for project in projects:
    update = project['lastUpdated']
    class_highlight = "class='highlight'" if update >= recent else ""
    print(f"<tr {class_highlight}><td><a href=#{project['_id']}>{project['name']}</a></td><td>{date2str(project['lastUpdated'])}</td><td>{get_user(project['lastUpdatedBy'])}</td></tr>")
print('</table>')

for project in projects:
    print(f"<h2 id={project['_id']}>{project['name']}</h2>")
    print(f"<a href='https://overleaf.theia.fe.up.pt/project/{project['_id']}'>Go to document</a>")
    docHist = db.docHistory.find({'project_id': project['_id']})
    print('<ul>')
    changes = []

    for i, hist in enumerate(docHist):
        #print(i, len(docHist), file=sys.stderr)
        filename = find_filename(project['rootFolder'], hist['doc_id'])
        if filename is None:
            filename = 'unknown'

        hist_pack = hist['pack']
        for pack in hist_pack:
            user_email = get_user(pack['meta']['user_id'])
            start_ts = datetime.fromtimestamp(pack['meta']['start_ts']//1000)
            end_ts = datetime.fromtimestamp(pack['meta']['end_ts']//1000)
            highlight = start_ts >= recent
            if not (start_ts > ago30days):
                continue
            for op in pack['op']:
                changes.append({'user_email': user_email, 'start_ts': start_ts, 'end_ts': end_ts, 'op': op, 'highlight': highlight, 'filename': filename})

    changes = sorted(changes, key=lambda change: change['end_ts'], reverse=True)
    for change in changes:
        class_highlight = "class='highlight'" if change['highlight'] else ""
        if 'i' in change['op']:
            text = change['op']['i'].replace('\n', r'\n')#.replace(' ', '&nbsp;')
            if len(text) == 0: continue
            print(f"<li><tt><span {class_highlight} style='color:gray'><b>{date2str(change['end_ts'])} {change['filename']}:{change['op']['p']}</b> added by <b>{change['user_email']}</b></span><br><span style='color:blue'>{text}</span></tt></li>")
            #print(f"<li><tt><span {class_highlight} style='color:gray'><b>{change['user_email']}</b> added {date2str(change['end_ts'])}</span><br><span style='color:blue'>{change['op']['i']}</span></tt></li>")
        elif 'd' in change['op']:
            text = change['op']['d'].replace('\n', r'\n')#.replace(' ', '&nbsp;')
            if len(text) == 0: continue
            print(f"<li><tt><span {class_highlight} style='color:gray'><b>{date2str(change['end_ts'])} {change['filename']}:{change['op']['p']}</b> removed by <b>{change['user_email']}</b></span><br><span style='color:red'><del>{text}</del></span></tt></li>")
            #print(f"<li><tt><span {class_highlight} style='color:gray'><b>{change['user_email']}</b> removed {date2str(change['end_ts'])}</span><br><span style='color:red'><del>{change['op']['d']}</del></span></tt></li>")
    print('</ul>')

print('</body>')
print('</html>')
