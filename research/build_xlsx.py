# -*- coding: utf-8 -*-
"""Build Global_Software_Developer_Training_and_Employment_Opportunities_2026.xlsx"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from data1_qatar_gcc_me import ROWS as R1
from data2_egypt_turkey_europe import ROWS as R2
from data3_americas_remote_global import ROWS as R3

ROWS = R1 + R2 + R3
CHECK_DATE = '2026-09-05'

# ---------- scoring ----------
def total(sc):
    return sum(sc)

def grade(t):
    return 'A+' if t >= 78 else 'A' if t >= 68 else 'B' if t >= 55 else 'C' if t >= 40 else 'D'

CUR_MAP = [('Qatar','QAR'),('Saudi','SAR'),('UAE','AED'),('Kuwait','KWD'),('Oman','OMR'),
           ('Jordan','JOD'),('Egypt','EGP'),('Turkey','TRY'),('UK','GBP'),('USA','USD'),
           ('US ','USD'),('Canada','CAD'),('Australia','AUD'),('New Zealand','NZD'),
           ('Germany','EUR'),('Netherlands','EUR'),('Portugal','EUR'),('Estonia','EUR'),
           ('Ireland','EUR'),('Poland','EUR'),('Sweden','SEK'),('Global','USD'),('Remote','USD'),('MENA','USD')]
def currency_for(row):
    s = row.get('sa','')
    for k,cur in [('QAR','QAR'),('SAR','SAR'),('AED','AED'),('KWD','KWD'),('OMR','OMR'),('JOD','JOD'),
                  ('EGP','EGP'),('TRY','TRY'),('GBP','GBP'),('USD','USD'),('CAD','CAD'),('AUD','AUD'),
                  ('NZD','NZD'),('EUR','EUR'),('SEK','SEK')]:
        if k in s: return cur
    for k,cur in CUR_MAP:
        if row['co'].startswith(k) or k in row['co']: return cur
    return ''

def yn(v, hi, mid):
    return hi if v >= 13 else mid if v >= 8 else 'Limited/No'

def employ_text(cv):
    if cv >= 13: return 'YES - strong documented pathway'
    if cv >= 10: return 'Likely - performance-based'
    if cv >= 7:  return 'Possible - not guaranteed'
    return 'Unlikely/Unknown'

def intl_text(i):
    return {'Y':'YES','N':'NO','U':'UNCLEAR'}[i]

RECS_ORDER = {'APPLY NOW':0,'HIGH PRIORITY':1,'GOOD TARGET':2,'APPLY IF REQUIREMENTS MET':3,'LOW PRIORITY':4,'TOP TARGET':0}
def rec_key(rc):
    for k,v in RECS_ORDER.items():
        if rc.startswith(k): return v
    return 3

recs = []
for r in ROWS:
    sc = r['sc']; t = total(sc)
    recs.append(dict(
        company=r['c'], ctype=r['ct'], title=r['ti'], otype=r['ot'], country=r['co'], city=r['ci'],
        remote=r['rm'], prio=r['pr'], techarea=r['ta'], techs=r['tech'], exp=r['ex'], degree=r['dg'],
        duration=r['du'], tr=sc[0], pj=sc[1], mn=sc[2], cv=sc[3], bg=sc[4], cs=sc[5], ts=sc[6],
        sl=sc[7], it=sc[8], score=t, grd=grade(t),
        training_provided=yn(sc[0],'Yes (structured)','Yes (some)'),
        mentor_provided=('Yes' if sc[2]>=7 else 'Partial' if sc[2]>=4 else 'Unclear'),
        real_projects=('Yes - production code' if sc[1]>=13 else 'Yes' if sc[1]>=9 else 'Limited'),
        employ_after=employ_text(sc[3]),
        salary=r['sa'], currency=currency_for(r), visa=r['vi'], reloc=r['re'], posted=r['po'],
        deadline=r['dl'], status=r['st'], url=r['u'], source=r['so'], last_checked=CHECK_DATE,
        difficulty=r['di'], beginner_suit=r['bs'], career_value=r['ca'], learning_value=r['le'],
        competition=r['cl'], requirements=r['rq'], skills_to_learn=r['sk'], why=r['wy'],
        risks=r['rk'], rec=r['rc'], notes=r['nt'], intl=intl_text(r['il']), risk=r['rl']))

recs.sort(key=lambda x: (-x['score'], x['prio'], -x['bg'], rec_key(x['rec'])))
for i, r in enumerate(recs, 1):
    r['rank'] = i

# dedupe sanity
seen = set()
for r in recs:
    k = (r['company'], r['title'])
    assert k not in seen, f'dup {k}'
    seen.add(k)

# ---------- workbook ----------
wb = Workbook()
wb.remove(wb.active)

HDR_FILL = PatternFill('solid', fgColor='1F3864')
HDR_FONT = Font(color='FFFFFF', bold=True, size=10)
BASE_FONT = Font(size=10)
LINK_FONT = Font(size=10, color='0563C1', underline='single')
THIN = Side(style='thin', color='D9D9D9')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
GRADE_FILL = {'A+':'C6EFCE','A':'E2EFDA','B':'FFF2CC','C':'FCE4D6','D':'F8CBAD'}
OPEN_FILL = PatternFill('solid', fgColor='C6EFCE')
CLOSED_FONT = Font(size=10, color='808080', italic=True)
WARN_FONT = Font(size=10, color='C55A11')

def style_header(ws, ncols, row=1):
    for c in range(1, ncols+1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HDR_FILL; cell.font = HDR_FONT
        cell.alignment = Alignment(vertical='center', wrap_text=True)
    ws.row_dimensions[row].height = 30

def write_table(ws, headers, rows_data, widths=None, wrap_cols=None, freeze='A2', link_col=None):
    ws.append(headers)
    style_header(ws, len(headers))
    for r in rows_data:
        ws.append(r)
    n = len(rows_data) + 1
    for c in range(1, len(headers)+1):
        L = get_column_letter(c)
        if widths: ws.column_dimensions[L].width = widths[c-1]
        for ri in range(2, n+1):
            cell = ws.cell(row=ri, column=c)
            cell.font = BASE_FONT
            cell.border = BORDER
            if wrap_cols and c in wrap_cols:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
            else:
                cell.alignment = Alignment(vertical='top')
    if link_col:
        for ri in range(2, n+1):
            cell = ws.cell(row=ri, column=link_col)
            if cell.value and str(cell.value).startswith('http'):
                cell.hyperlink = cell.value
                cell.font = LINK_FONT
    if freeze: ws.freeze_panes = freeze
    ws.auto_filter.ref = f'A1:{get_column_letter(len(headers))}{max(n,2)}'
    return n

# ---------- Sheet 1: ALL ----------
H1 = ['Rank','Overall Score','Grade','Priority','Country','City','Remote/On-site/Hybrid','Company',
      'Company Type','Job Title','Opportunity Type','Technology Area','Technologies','Experience Required',
      'Degree Required','Duration','Training Provided','Mentor Provided','Real Project Experience',
      'Employment After Training','Full-Time Conversion','Salary','Currency','Visa Sponsorship',
      'Relocation Support','Application Deadline','Posted Date','Status','Official Application Link',
      'Source','Last Checked','Difficulty','Suitability for Beginner','Career Value','Learning Value',
      'Competition Level','Important Requirements','Skills to Learn Before Applying','Why It Is Good',
      'Risks / Disadvantages','AI Recommendation','Notes','Risk Level','Can Apply Internationally']
ws = wb.create_sheet('ALL_OPPORTUNITIES')
rows1 = []
for r in recs:
    ft_conv = employ_text(r['cv'])
    rows1.append([r['rank'], r['score'], r['grd'], r['prio'], r['country'], r['city'], r['remote'],
        r['company'], r['ctype'], r['title'], r['otype'], r['techarea'], r['techs'], r['exp'], r['degree'],
        r['duration'], r['training_provided'], r['mentor_provided'], r['real_projects'], r['employ_after'],
        ft_conv, r['salary'], r['currency'], r['visa'], r['reloc'], r['deadline'], r['posted'], r['status'],
        r['url'], r['source'], r['last_checked'], r['difficulty'], r['beginner_suit'], r['career_value'],
        r['learning_value'], r['competition'], r['requirements'], r['skills_to_learn'], r['why'], r['risks'],
        r['rec'], r['notes'], r['risk'], r['intl']])
W1 = [6,8,7,8,14,12,12,20,18,34,18,24,34,18,20,20,13,11,14,24,24,26,9,22,13,24,18,22,46,26,11,16,24,26,20,14,34,28,36,34,26,24,10,12]
n1 = write_table(ws, H1, rows1, W1, wrap_cols=set(range(1,45)), freeze='D2', link_col=29)
for ri in range(2, n1+1):
    g = ws.cell(row=ri, column=3).value
    ws.cell(row=ri, column=3).fill = PatternFill('solid', fgColor=GRADE_FILL.get(g,'FFFFFF'))
    st_txt = str(ws.cell(row=ri, column=28).value)
    if st_txt.upper().startswith('OPEN'): ws.cell(row=ri, column=28).fill = OPEN_FILL
    elif 'losed' in st_txt or 'CLOS' in st_txt.upper(): ws.cell(row=ri, column=28).font = CLOSED_FONT
    if st_txt.startswith('Unverified'): ws.cell(row=ri, column=28).font = WARN_FONT

# ---------- Sheet 2: TOP 50 ----------
ws = wb.create_sheet('TOP 50')
H2 = ['Rank','Company','Position','Country','Score','Grade','Why Recommended','Training','Employment Potential','Salary','Visa','Deadline','Application Link']
rows2 = []
for r in recs[:50]:
    rows2.append([r['rank'], r['company'], r['title'], r['country'], r['score'], r['grd'], r['why'],
                  r['training_provided'], r['employ_after'], r['salary'], r['visa'], r['deadline'], r['url']])
n2 = write_table(ws, H2, rows2, [6,20,36,18,8,7,44,13,26,26,22,26,50],
                 wrap_cols={3,7,10,11,12,13}, freeze='C2', link_col=13)
for ri in range(2, n2+1):
    g = ws.cell(row=ri, column=6).value
    ws.cell(row=ri, column=6).fill = PatternFill('solid', fgColor=GRADE_FILL.get(g,'FFFFFF'))

# ---------- Sheet 3: QATAR ----------
ws = wb.create_sheet('QATAR')
H3 = ['Rank','Score','Grade','Company','Job Title','Opportunity Type','City','Technologies','Experience Required',
      'Training Provided','Mentor','Real Projects','Employment After','Salary','Deadline','Status','AI Recommendation',
      'Why It Is Good','Risks','Application Link','Notes']
qatar = [r for r in recs if r['country'].startswith('Qatar')]
rows3 = [[r['rank'], r['score'], r['grd'], r['company'], r['title'], r['otype'], r['city'], r['techs'], r['exp'],
          r['training_provided'], r['mentor_provided'], r['real_projects'], r['employ_after'], r['salary'],
          r['deadline'], r['status'], r['rec'], r['why'], r['risks'], r['url'], r['notes']] for r in qatar]
n3 = write_table(ws, H3, rows3, [6,7,7,18,34,18,12,30,18,13,9,13,24,24,22,20,24,34,30,44,22],
                 wrap_cols=set(range(4,22)), freeze='D2', link_col=20)
for ri in range(2, n3+1):
    g = ws.cell(row=ri, column=3).value
    ws.cell(row=ri, column=3).fill = PatternFill('solid', fgColor=GRADE_FILL.get(g,'FFFFFF'))

# ---------- Sheet 4: TRAINING_TO_EMPLOYMENT ----------
ws = wb.create_sheet('TRAINING_TO_EMPLOYMENT')
H4 = ['Rank','Score','Company','Program','Country','Path (Training -> Employment)','Conversion Evidence','Employment Potential',
      'Conversion Score /15','Beginner Fit','Salary','Status','Application Link','Why / Notes']
def conv_evidence(r):
    ev = []
    if r['cv'] >= 13: ev.append('Documented conversion/employment pathway')
    if 'convert' in (r['employ_after']+r['notes']+r['why']).lower(): ev.append('Conversion explicitly stated')
    if r['otype'] in ('Graduate Program','Trainee Program','Apprenticeship','Bootcamp-to-Employment','Government Program'): ev.append('Program type designed to hire')
    return '; '.join(dict.fromkeys(ev)) or 'Pathway implied by program structure'
tte = [r for r in recs if (r['cv'] >= 11) or (r['otype'] in ('Graduate Program','Trainee Program','Apprenticeship','Bootcamp-to-Employment') and r['cv'] >= 9)]
tte.sort(key=lambda x: (-x['cv'], -x['score']))
rows4 = []
for r in tte:
    path = ''
    if r['otype'] in ('Graduate Program','Trainee Program'): path = 'Training -> Graduate/Trainee -> Full-Time'
    elif r['otype'] == 'Apprenticeship': path = 'Apprenticeship -> Employment'
    elif r['otype'] == 'Bootcamp-to-Employment': path = 'Academy/Bootcamp -> Employment'
    elif r['otype'] == 'Internship': path = 'Internship -> Graduate -> Full-Time'
    elif r['otype'] == 'Government Program': path = 'Government Training -> Employer Pipeline'
    else: path = 'Training -> Employment pathway'
    rows4.append([r['rank'], r['score'], r['company'], r['title'], r['country'], path, conv_evidence(r),
                  r['employ_after'], r['cv'], r['bg'], r['salary'], r['status'], r['url'], r['notes'] or r['why']])
n4 = write_table(ws, H4, rows4, [6,7,20,34,16,30,32,24,10,10,24,20,46,28],
                 wrap_cols={4,6,7,8,11,12,13,14}, freeze='C2', link_col=13)

# ---------- Sheet 5: REMOTE_GLOBAL ----------
ws = wb.create_sheet('REMOTE_GLOBAL')
H5 = ['Score','Grade','Company','Role','HQ Country / Scope','Remote Scope','Can Apply Internationally?','Salary','Status','Deadline','Application Link','Notes']
rg = [r for r in recs if ('Remote' in r['remote'] or r['remote'] == 'Remote' or r['country'] in ('Global (remote)','Remote','MENA (remote)') or 'remote' in r['city'].lower())]
rows5 = [[r['score'], r['grd'], r['company'], r['title'], r['country'], r['remote'], r['intl'], r['salary'],
          r['status'], r['deadline'], r['url'], (r['notes'] or '') + (' | ' + r['risks'] if r['risks'] else '')] for r in rg]
n5 = write_table(ws, H5, rows5, [7,7,20,36,20,16,16,24,22,24,44,34],
                 wrap_cols={4,8,9,10,11,12}, freeze='C2', link_col=11)
for ri in range(2, n5+1):
    g = ws.cell(row=ri, column=2).value
    ws.cell(row=ri, column=2).fill = PatternFill('solid', fgColor=GRADE_FILL.get(g,'FFFFFF'))

# ---------- Sheet 6: COUNTRY_SUMMARY ----------
def bucket_country(c):
    if c.startswith('Qatar'): return 'Qatar'
    if c.startswith('Saudi'): return 'Saudi Arabia'
    if c.startswith('UAE'): return 'UAE'
    if c.startswith('US'): return 'USA'
    for k in ['Kuwait','Oman','Jordan','Egypt','Turkey','Portugal','Germany','Netherlands',
              'Ireland','UK','Sweden','Estonia','Poland','Canada','Australia','New Zealand']:
        if c.startswith(k): return k
    if 'Global' in c: return 'Remote/Global'
    if c.startswith('MENA'): return 'Remote/Global'
    if c.startswith('Remote'): return 'Remote/Global'
    return c.split('(')[0].split('/')[0].strip()
from collections import defaultdict, OrderedDict
cs = defaultdict(list)
for r in recs: cs[bucket_country(r['country'])].append(r)
ws = wb.create_sheet('COUNTRY_SUMMARY')
H6 = ['Country','Opportunities Found','Open Opportunities','Beginner Friendly','Training Programs','Employment Programs','Average Score','Best Opportunity (highest score)']
rows6 = []
for country, lst in sorted(cs.items(), key=lambda kv: -sum(x['score'] for x in kv[1])/len(kv[1])):
    best = max(lst, key=lambda x: x['score'])
    rows6.append([country, len(lst),
                  sum(1 for x in lst if x['status'].upper().startswith('OPEN')),
                  sum(1 for x in lst if x['bg'] >= 8),
                  sum(1 for x in lst if x['tr'] >= 13),
                  sum(1 for x in lst if x['cv'] >= 11),
                  round(sum(x['score'] for x in lst)/len(lst), 1),
                  f"{best['company']} - {best['title']} ({best['score']})"])
n6 = write_table(ws, H6, rows6, [18,12,12,12,12,13,12,60], wrap_cols={8}, freeze='B2')

# ---------- Sheet 7: COMPANY_SUMMARY ----------
co = defaultdict(list)
for r in recs: co[r['company']].append(r)
ws = wb.create_sheet('COMPANY_SUMMARY')
H7 = ['Company','Country/Scope','Number of Opportunities','Training Programs','Graduate Programs','Junior Jobs','Conversion Potential (avg cv /15)','Average Score']
rows7 = []
for company, lst in sorted(co.items(), key=lambda kv: -sum(x['score'] for x in kv[1])/len(kv[1])):
    rows7.append([company, lst[0]['country'], len(lst),
                  sum(1 for x in lst if x['tr'] >= 13),
                  sum(1 for x in lst if 'Graduate' in x['otype'] or 'Trainee' in x['otype']),
                  sum(1 for x in lst if 'Junior' in x['otype'] or 'Junior' in x['title']),
                  round(sum(x['cv'] for x in lst)/len(lst),1),
                  round(sum(x['score'] for x in lst)/len(lst),1)])
write_table(ws, H7, rows7, [30,26,12,12,12,10,14,12], wrap_cols={2}, freeze='B2')

# ---------- Sheet 8: SKILLS_ANALYSIS ----------
KW = [
 ('Python', r'\bpython\b'), ('JavaScript', r'javascript|\bjs\b|\bnode\b'), ('TypeScript', r'typescript'),
 ('Java', r'\bjava\b(?!script)'), ('C#/.NET', r'c#|\.net'), ('Go/Golang', r'\bgo(lang)?\b'),
 ('SQL (any)', r'\bsql\b'), ('PostgreSQL', r'postgres'), ('Oracle PL/SQL', r'oracle|pl/sql'),
 ('Git/GitHub', r'\bgit\b|github'), ('React', r'react'), ('Node.js', r'node\.?js'),
 ('Docker/Containers', r'docker|container'), ('Kubernetes', r'kubernetes|k8s'),
 ('AWS/Cloud', r'\baws\b|\bcloud\b'), ('Azure', r'azure'), ('Linux/Unix', r'linux|unix'),
 ('REST APIs', r'\brest\b|\bapi\b'), ('Testing/TDD/QA', r'test|tdd|\bqa\b'),
 ('Spring Boot', r'spring'), ('C/C++', r'\bc\+\+|\bc\b(?!#)'), ('PHP', r'\bphp\b'),
 ('Ruby/Rails', r'ruby|rails'), ('Mobile (iOS/Android)', r'ios|android|flutter|mobile'),
 ('ML/AI', r'\bml\b|machine learning|\bai\b|llm'), ('Unity/Game', r'unity|game'),
 ('HTML/CSS/Web basics', r'html|css|web'), ('Data Engineering', r'data engineer|pipeline|warehouse'),
]
full_text = lambda r: ' '.join([r['techs'], r['techarea'], r['title'], r['career_value']]).lower()
ws = wb.create_sheet('SKILLS_ANALYSIS')
H8 = ['Skill','Number of Jobs','Percentage of All Opportunities','Importance','Note for Beginners']
total_n = len(recs)
rows8 = []
for name, pat in KW:
    cnt = sum(1 for r in recs if re.search(pat, full_text(r)))
    if cnt == 0: continue
    junior_cnt = sum(1 for r in recs if r['bg'] >= 7 and re.search(pat, full_text(r)))
    imp = 'Critical' if cnt >= 18 else 'High' if cnt >= 10 else 'Medium' if cnt >= 5 else 'Niche'
    note = {'Critical':'Learn early - core junior-market currency',
            'High':'Strong differentiator for junior roles',
            'Medium':'Useful; learn when relevant to target stack',
            'Niche':'Optional specialization'}.get(imp, '')
    if junior_cnt and imp in ('Critical','High'):
        note += f' (required/valued in {junior_cnt} beginner-friendly listings)'
    rows8.append([name, cnt, f'{cnt/total_n*100:.0f}%', imp, note])
rows8.sort(key=lambda x: -x[1])
n8 = write_table(ws, H8, rows8, [24,12,16,12,50], wrap_cols={5}, freeze='B2')
adv = [
 '', 'SKILL GAP ANALYSIS (assumed profile: Python + Git/GitHub + basic SQL + GitHub projects, no professional experience)',
 'Target 1 - Qatar/GCC junior & intern roles: Required = Python/JS + SQL + Git + REST basics -> Missing = 1 production-grade project, REST/HTTP depth, basic testing -> Difficulty: LOW-MEDIUM (achievable in 2-3 months)',
 'Target 2 - GCC graduate programs (stc TIP, Aramco, SAMA): Required = degree + GPA (3.0-3.7) + English (IELTS 5+) + interview skills -> Missing = certificates/IELTS, GPA evidence, DSA practice -> Difficulty: MEDIUM (depends on your degree/GPA)',
 'Target 3 - Remote global junior (Canonical, Blip, remote MENA): Required = strong Python/TypeScript + Git workflow + one modern framework (React/Node or Django) + Docker basics -> Missing = framework depth, Docker, CI familiarity, OSS contribution history -> Difficulty: MEDIUM (3-6 months focused work)',
 'Target 4 - Big-tech new grad (Google/Amazon/Microsoft): Required = DSA mastery + behavioral prep -> Missing = 150-300 LeetCode-style problems, system design basics -> Difficulty: HIGH (4-8 months)',
 'LEARN FIRST (highest ROI): 1) Git/GitHub workflow 2) Python OR JavaScript depth 3) SQL 4) REST APIs + HTTP 5) Testing basics (pytest/Jest) 6) One framework (React or Django/FastAPI or Spring) 7) Docker basics 8) DSA fundamentals for interviews',
]
start = n8 + 2
for i, line in enumerate(adv):
    cell = ws.cell(row=start+i, column=1, value=line)
    cell.font = Font(size=10, bold=(i in (1,6)), color='1F3864' if i in (1,6) else '000000')
    cell.alignment = Alignment(wrap_text=True, vertical='top')

# ---------- Sheet 9: READ_ME ----------
ws = wb.create_sheet('READ_ME')
lines = [
 ('Global Software Developer - Training & Employment Opportunities 2026', True),
 ('Generated: 2026-09-05 | Method: multi-stage global scan (Qatar -> GCC -> Middle East -> Europe -> Americas -> AU/NZ -> Remote -> Government/Apprenticeship -> Startups -> Big Tech), 50+ targeted searches, links taken from official pages or listings seen during the scan.', False),
 ('', False),
 ('HOW TO USE', True),
 ('1) Open ALL_OPPORTUNITIES - sorted by Overall Score (best first). Rank 1 = start here.', False),
 ('2) Filter Status = OPEN for currently-open opportunities; Annual = programs that recur every year (set calendar reminders for their windows).', False),
 ('3) Use TOP 50 for the shortlist; QATAR for the deep local dive; TRAINING_TO_EMPLOYMENT for programs with the clearest hiring pipeline; REMOTE_GLOBAL for location-free options.', False),
 ('4) SKILLS_ANALYSIS shows what the market asks for and a personal skill-gap plan.', False),
 ('', False),
 ('SCORING RUBRIC (total 100)', True),
 ('Training quality 20 | Real project experience 20 | Mentor/senior access 10 | Employment after training 15 | Beginner fit 10 | Company strength 10 | Technology stack 5 | Salary/support 5 | International/visa/remote 5', False),
 ('Grades (calibrated to this dataset, top score = 84): A+ >= 78 (apply immediately if eligible) | A >= 68 | B >= 55 | C >= 40 | D < 42', False),
 ('', False),
 ('STATUS LEGEND', True),
 ('OPEN = verified open within days of 2026-09-05. Open/Unverified or Unverified = seen active recently but could not re-confirm - always verify on the official page before applying.', False),
 ('Annual / Closed = recurring program whose current cycle closed (deadline noted) - prepare for the next window.', False),
 ('Rolling = always-open pipeline or weekly vacancies.', False),
 ('', False),
 ('ASSUMED USER PROFILE (used for AI Recommendation and Skill Gap)', True),
 ('Early-career developer: Python + Git/GitHub + basic SQL + personal GitHub projects; limited professional experience; based in Qatar; Arabic/English. Adjust filters if your profile differs.', False),
 ('', False),
 ('ANTI-FRAUD RULES', True),
 ('- Never pay any fee to get a job or internship. Legitimate employers pay YOU (except clearly-disclosed tuition bootcamps).', False),
 ('- Verify every company domain; apply only via official career portals (column "Official Application Link").', False),
 ('- "AI pilot" / gig listings (e.g., Mindrift row) are freelance gigs, not career experience - flagged Risk Level = Medium.', False),
 ('- Visa: no legitimate employer asks you to pay for sponsorship. GCC programs are often nationality-restricted (noted per row).', False),
 ('', False),
 ('KEY CAVEATS', True),
 ('- Postings change daily; deadlines were correct at check time (2026-09-05). Re-verify before applying.', False),
 ('- Salary figures marked "secondary/reported" come from market guides, not official offers.', False),
 ('- Deduplication applied: one row per distinct program/role (aggregator duplicates of the same listing were merged).', False),
 ('- Bahrain: no verified junior-tech program rows found in this scan; check Tamkeen (tamkeen.bh) programs directly.', False),
]
for i,(txt,bold) in enumerate(lines, 1):
    cell = ws.cell(row=i, column=1, value=txt)
    cell.font = Font(size=11 if bold else 10, bold=bold, color='1F3864' if bold else '000000')
    cell.alignment = Alignment(wrap_text=True, vertical='top')
ws.column_dimensions['A'].width = 150

out = '/home/user/game/Global_Software_Developer_Training_and_Employment_Opportunities_2026.xlsx'
wb.save(out)
print('rows:', len(recs), '| sheets:', wb.sheetnames)
print('open rows:', sum(1 for r in recs if r['status'].upper().startswith('OPEN')))
print('grades:', {g: sum(1 for r in recs if r['grd']==g) for g in ['A+','A','B','C','D']})
print('saved:', out)
