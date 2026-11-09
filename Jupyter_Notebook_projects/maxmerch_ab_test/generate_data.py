# -*- coding: utf-8 -*-
from pathlib import Path
import csv, json, math, random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(parents=True, exist_ok=True)
SEED = 20260917
rng = np.random.default_rng(SEED)
random.seed(SEED)

# ---------- Reference entities ----------
cities = ['Almaty','Astana','Shymkent','Karaganda','Aktobe','Atyrau']
city_w = [0.34,0.22,0.16,0.11,0.09,0.08]
platforms = ['Android','iOS']
channels = ['Modern trade','Convenience','Traditional trade']
client_names = ['North Star Foods','Steppe Drinks','Dala Dairy','Orion Home','Qanat Snacks','Arman Personal Care']
project_rows=[]
for i in range(1,19):
    client=client_names[(i-1)%len(client_names)]
    project_rows.append({'project_id':f'PRJ{i:03d}','client_name':client,'project_name':f'{client.split()[0]} Field Execution {((i-1)//6)+1}','category':['Beverages','Dairy','Snacks','Household','Personal care','Food'][((i-1)//3)%6],'active_from':'2025-08-01','active_to':'2025-10-31'})
projects=pd.DataFrame(project_rows)

outlet_rows=[]
for i in range(1,1801):
    city=rng.choice(cities,p=city_w)
    outlet_rows.append({'outlet_id':f'TT{i:05d}','outlet_name':f'{city} Retail Point {i:04d}','city':city,'channel':rng.choice(channels,p=[.42,.25,.33]),'format':rng.choice(['Small','Medium','Large'],p=[.48,.37,.15])})
outlets=pd.DataFrame(outlet_rows)
outlet_city=dict(zip(outlets.outlet_id,outlets.city))

# ---------- Users and stratified individual randomization ----------
N_USERS=3000
users=[]
for i in range(1,N_USERS+1):
    city=rng.choice(cities,p=city_w)
    tenure=int(np.clip(rng.gamma(2.0,11.0),1,72))
    tenure_band='0-6m' if tenure<=6 else ('7-18m' if tenure<=18 else '19m+')
    users.append({'merchandiser_id':f'M{i:05d}','city':city,'tenure_months':tenure,'tenure_band':tenure_band,'platform':rng.choice(platforms,p=[.77,.23]),'team_id':f'TEAM{(i-1)//12+1:04d}','employment_type':rng.choice(['Full-time','Contractor'],p=[.82,.18])})
merch=pd.DataFrame(users)
# deterministic 1:1 within city x tenure band x platform strata (pairs)
assignment=[]
leftovers=[]
for _,g in merch.groupby(['city','tenure_band','platform'],sort=True):
    ids=g.merchandiser_id.to_numpy().copy(); rng.shuffle(ids)
    paired=ids[:(len(ids)//2)*2]
    for j in range(0,len(paired),2):
        pair=paired[j:j+2].copy(); rng.shuffle(pair)
        assignment.extend([(pair[0],'control'),(pair[1],'treatment')])
    if len(ids)%2: leftovers.append(ids[-1])
leftovers=np.array(leftovers,dtype=object); rng.shuffle(leftovers)
need_treatment=N_USERS//2-sum(1 for _,label in assignment if label=='treatment')
assignment.extend((uid,'treatment' if i<need_treatment else 'control') for i,uid in enumerate(leftovers))
ass=pd.DataFrame(assignment,columns=['merchandiser_id','group'])
ass['assigned_at']='2025-09-15 00:00:00'
ass['randomization_unit']='merchandiser'
ass=ass.merge(merch[['merchandiser_id','city','tenure_months','tenure_band','platform','team_id']],on='merchandiser_id',how='left')
ass.to_csv(DATA/'experiment_assignments.csv',index=False)
merch.to_csv(DATA/'merchandisers.csv',index=False)
outlets.to_csv(DATA/'outlets.csv',index=False)
projects.to_csv(DATA/'projects.csv',index=False)
group_map=dict(zip(ass.merchandiser_id,ass.group))

# ---------- Visits and task-level source data ----------
pre_dates=pd.bdate_range('2025-09-01','2025-09-12')
exp_dates=pd.bdate_range('2025-09-15','2025-10-24')
visit_rows=[]
task_rows=[]
event_rows=[]
visit_counter=0
task_counter=0
event_counter=0
# persistent employee ability creates within-person correlation
ability={u:float(rng.normal(0,.012)) for u in merch.merchandiser_id}
project_ids=projects.project_id.to_numpy()
outlet_ids=outlets.outlet_id.to_numpy()
for _,u in merch.iterrows():
    uid=u.merchandiser_id
    group=group_map[uid]
    # Repeated visits per workday, varied but operationally plausible.
    for phase, dates in [('pre',pre_dates),('experiment',exp_dates)]:
        for day in dates:
            n_visits=int(rng.choice([1,2,3,4],p=[.08,.34,.43,.15]))
            day_outlets=rng.choice(outlet_ids,size=n_visits,replace=False)
            for j,outlet in enumerate(day_outlets):
                visit_counter+=1
                vid=f'V{visit_counter:08d}'
                project=str(rng.choice(project_ids))
                planned_hour=int(rng.integers(8,16))
                planned_min=int(rng.choice([0,15,30,45]))
                planned=datetime(day.year,day.month,day.day,planned_hour,planned_min)
                # Missed/cancelled visits remain in the denominator (ITT) and have no completion timestamp.
                cancelled=bool(rng.random()<.035)
                start=None if cancelled or rng.random()<.018 else planned+timedelta(minutes=int(rng.normal(5,18)))
                screen_exposed=phase=='experiment' and group=='treatment' and bool(start) and rng.random()<.89
                dur=int(np.clip(rng.normal(39,13),12,105)) if start else None
                if screen_exposed and rng.random()<.70:
                    # The new screen slightly shortens successful navigation time.
                    dur=max(10,dur-int(rng.integers(1,4)))
                end=start+timedelta(minutes=dur) if start else None
                visit_rows.append({'visit_id':vid,'merchandiser_id':uid,'outlet_id':outlet,'project_id':project,'phase':phase,'scheduled_at':planned.strftime('%Y-%m-%d %H:%M:%S'),'actual_start_at':start.strftime('%Y-%m-%d %H:%M:%S') if start else '', 'actual_end_at':end.strftime('%Y-%m-%d %H:%M:%S') if end else '', 'visit_status':'cancelled' if cancelled else ('completed' if start else 'no_show'),'group':group,'device_platform':u.platform,'city':u.city})
                # exactly 3 required tasks; survey is a fourth required item on 70% of visits
                n_req=4 if rng.random()<.70 else 3
                for k in range(n_req):
                    task_counter+=1
                    tid=f'TK{task_counter:09d}'
                    task_type=['shelf_audit','price_check','photo_evidence','questionnaire'][k]
                    is_required=True
                    if k==3 and n_req<4: continue
                    base_p=.922 + ability[uid]
                    if screen_exposed: base_p += .0018
                    base_p=float(np.clip(base_p,.84,.97))
                    completed=bool(start and rng.random()<base_p)
                    if completed and end:
                        offset=int(rng.integers(2,max(3,dur-1)))
                        completed_at=(start+timedelta(minutes=offset)).strftime('%Y-%m-%d %H:%M:%S')
                    else: completed_at=''
                    task_rows.append({'task_id':tid,'visit_id':vid,'task_type':task_type,'is_required':is_required,'task_status':'completed' if completed else ('not_applicable' if cancelled else 'incomplete'),'completed_at':completed_at,'priority':['high','medium','medium','high'][k]})
                # lightweight application events; exposure and completion are separately measurable
                if phase=='experiment':
                    if group=='control' and start and rng.random()<.015:
                        event_counter+=1; event_rows.append({'event_id':f'E{event_counter:09d}','visit_id':vid,'merchandiser_id':uid,'event_name':'legacy_task_list_opened','event_at':start.strftime('%Y-%m-%d %H:%M:%S'),'group':group})
                    if screen_exposed:
                        event_counter+=1; event_rows.append({'event_id':f'E{event_counter:09d}','visit_id':vid,'merchandiser_id':uid,'event_name':'priority_screen_opened','event_at':start.strftime('%Y-%m-%d %H:%M:%S'),'group':group})
                    if start and rng.random()<.96:
                        event_counter+=1; event_rows.append({'event_id':f'E{event_counter:09d}','visit_id':vid,'merchandiser_id':uid,'event_name':'visit_workspace_opened','event_at':start.strftime('%Y-%m-%d %H:%M:%S'),'group':group})
                    if start and rng.random()<.004:
                        event_counter+=1; event_rows.append({'event_id':f'E{event_counter:09d}','visit_id':vid,'merchandiser_id':uid,'event_name':'app_error','event_at':start.strftime('%Y-%m-%d %H:%M:%S'),'group':group})
                    if start and rng.random()<.0008:
                        event_counter+=1; event_rows.append({'event_id':f'E{event_counter:09d}','visit_id':vid,'merchandiser_id':uid,'event_name':'support_ticket_created','event_at':start.strftime('%Y-%m-%d %H:%M:%S'),'group':group})

visits=pd.DataFrame(visit_rows)
tasks=pd.DataFrame(task_rows)
events=pd.DataFrame(event_rows)
# Introduce small, documented raw-data quality issues that the notebook must detect and handle.
# Duplicate visit rows are exact transport duplicates; no other keys are intentionally corrupted.
dup_n=max(1,int(len(visits)*0.0015))
dup_idx=rng.choice(visits.index.to_numpy(),size=dup_n,replace=False)
visits=pd.concat([visits,visits.loc[dup_idx]],ignore_index=True)
# A small number of missing timestamps are already naturally present from cancellations/no-shows.
visits.to_csv(DATA/'visits.csv',index=False)
tasks.to_csv(DATA/'tasks.csv',index=False)
events.to_csv(DATA/'events.csv',index=False)

# Data dictionary and reproducibility metadata
metadata={
 'project':'MAXMERCH merchandiser task-prioritization A/B test',
 'synthetic':True,
 'seed':SEED,
 'generated_at':'2026-11-09',
 'experiment_period':['2025-09-15','2025-10-24'],
 'pre_period':['2025-09-01','2025-09-12'],
 'users':int(len(merch)), 'assignments':int(len(ass)),
 'visits_raw_with_transport_duplicates':int(len(visits)),
 'unique_visit_ids':int(visits.visit_id.nunique()),
 'task_rows':int(len(tasks)), 'event_rows':int(len(events)),
 'raw_data_issues':['0.15% exact duplicate visit records were appended to simulate transport duplication','no-show and cancelled visits have missing actual timestamps by design']
}
(ROOT/'data_generation_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')

# ---------- Notebook ----------
md=lambda s:{'cell_type':'markdown','metadata':{},'source':s.splitlines(True)}
code=lambda s:{'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':s.splitlines(True)}
cells=[
md("""# MAXMERCH: A/B-тест экрана приоритизации задач мерчендайзера\n\n**Портфолио-кейс, вымышленная компания и смоделированные данные.** MAXMERCH — условное B2B-приложение для планирования визитов мерчендайзеров в торговые точки. Данные сгенерированы детерминированно (seed 20260917) и не относятся к реальной компании или клиентскому заказу.\n\n**Задача:** оценить, повышает ли новый экран с группировкой и приоритетами задач долю визитов с выполненными обязательными задачами, не ухудшая операционные метрики.\n\n**Эксперимент:** индивидуальная рандомизация мерчендайзеров 1:1, 2 недели pre-period и 6 недель теста; анализ intention-to-treat (ITT). Единица анализа для основного вывода — мерчендайзер, поскольку на него закрепляется вариант и его визиты зависимы друг от друга.\n"""),
md("""## 1. Импорт и загрузка данных\n\nВ проекте 2 400 мерчендайзеров и более 150 000 строк визитов. Таблицы связаны ключами: `merchandiser_id`, `visit_id`, `outlet_id`, `project_id`.\n"""),
code("""from pathlib import Path\nimport warnings\nwarnings.filterwarnings('ignore')\nimport numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\nfrom scipy import stats\n\npd.set_option('display.max_columns', 50)\npd.set_option('display.float_format', lambda x: f'{x:,.4f}')\nDATA_DIR = Path('data')\nmerch = pd.read_csv(DATA_DIR / 'merchandisers.csv')\nassign = pd.read_csv(DATA_DIR / 'experiment_assignments.csv')\noutlets = pd.read_csv(DATA_DIR / 'outlets.csv')\nprojects = pd.read_csv(DATA_DIR / 'projects.csv')\nvisits_raw = pd.read_csv(DATA_DIR / 'visits.csv')\ntasks = pd.read_csv(DATA_DIR / 'tasks.csv')\nevents = pd.read_csv(DATA_DIR / 'events.csv')\nprint({name: len(frame) for name, frame in {'merchandisers':merch,'assignments':assign,'visits_raw':visits_raw,'tasks':tasks,'events':events}.items()})\n"""),
md("""## 2. Формулировка гипотез и правила решения\n\n**Основная метрика:** доля запланированных визитов мерчендайзера, где выполнены все обязательные задачи. Отменённые, пропущенные и незавершённые визиты остаются в ITT-знаменателе и дают `0` по основной метрике.\n\n- **H₀:** средняя доля успешных визитов в тестовой и контрольной группах одинакова (Δ = 0).\n- **H₁:** средняя доля успешных визитов различается (Δ ≠ 0), двусторонняя проверка.\n- **α = 0,05**, мощность планирования **80%**.\n- **MDE для бизнес-решения:** +1,0 процентный пункт (п.п.).\n- Статистическая значимость оценивается по p-value и 95% ДИ. Практическое решение дополнительно учитывает MDE и защитные метрики.\n\nПоскольку рандомизация на уровне мерчендайзера, повторные визиты нельзя считать независимыми наблюдениями. Основной тест проводится на агрегированной метрике каждого мерчендайзера (Welch t-test). Визитный z-тест показан только как наивная иллюстрация и не используется для решения.\n"""),
md("""## 3. Проверка структуры и качества исходных данных\n\nСначала проверяем ключи, дубликаты, пропуски, даты и соответствие связей. Технические дубликаты визитов удаляются по `visit_id`; отмены и no-show не удаляются, так как они относятся к исходу по ITT.\n"""),
code("""# Обзор схемы, размеров, ключей и пропусков\nquality = pd.DataFrame({\n    'rows': {'visits_raw':len(visits_raw),'tasks':len(tasks),'events':len(events)},\n    'duplicate_keys': {'visits_raw':int(visits_raw.visit_id.duplicated().sum()),'tasks':int(tasks.task_id.duplicated().sum()),'events':int(events.event_id.duplicated().sum())},\n    'missing_cells': {'visits_raw':int(visits_raw.isna().sum().sum()),'tasks':int(tasks.isna().sum().sum()),'events':int(events.isna().sum().sum())}\n})\ndisplay(quality)\nprint('Group assignment:', assign.group.value_counts().to_dict())\nprint('Visit status:', visits_raw.visit_status.value_counts(dropna=False).to_dict())\nprint('Phase:', visits_raw.phase.value_counts().to_dict())\nprint('Foreign keys:')\nprint(' unknown merchandisers:', (~visits_raw.merchandiser_id.isin(merch.merchandiser_id)).sum())\nprint(' unknown outlets:', (~visits_raw.outlet_id.isin(outlets.outlet_id)).sum())\nprint(' unknown projects:', (~visits_raw.project_id.isin(projects.project_id)).sum())\n"""),
code("""# Предобработка: удаляем только точные дубли visit_id, парсим даты, отмечаем невалидную длительность\nvisits = visits_raw.drop_duplicates('visit_id', keep='first').copy()\nfor c in ['scheduled_at','actual_start_at','actual_end_at']:\n    visits[c] = pd.to_datetime(visits[c], errors='coerce')\nvisits['duration_min'] = (visits.actual_end_at - visits.actual_start_at).dt.total_seconds()/60\nvisits['invalid_duration'] = visits.duration_min.notna() & ((visits.duration_min <= 0) | (visits.duration_min > 240))\n# Для duration guardrail не обрезаем выбросы молча: сохраняем валидный флаг, invalid остаётся видимым в аудите.\nprint(f'Удалено повторных visit_id: {len(visits_raw)-len(visits):,}')\nprint(f'Уникальные визиты после дедупликации: {len(visits):,}')\nprint('Missing actual start/end (mostly no-show/cancelled):', visits[['actual_start_at','actual_end_at']].isna().sum().to_dict())\nprint('Invalid duration count:', int(visits.invalid_duration.sum()))\nassert visits.visit_id.is_unique\nassert set(assign.group.unique()) == {'control','treatment'}\n"""),
md("""## 4. Сборка аналитической таблицы\n\nРезультат визита выводится из `tasks.csv`, а не берётся готовым полем: все задачи с `is_required=True` должны иметь статус `completed`. Для каждого назначенного мерчендайзера считаем долю успешных визитов за период эксперимента.\n"""),
code("""task_rollup = (tasks.assign(is_required=tasks.is_required.astype(bool), is_completed=tasks.task_status.eq('completed'))\n    .query('is_required')\n    .groupby('visit_id')\n    .agg(required_tasks=('task_id','size'), completed_required=('is_completed','sum'))\n    .reset_index())\ntask_rollup['all_required_complete'] = task_rollup.completed_required.eq(task_rollup.required_tasks)\nanalysis = visits.merge(task_rollup, on='visit_id', how='left', validate='one_to_one')\nanalysis[['required_tasks','completed_required']] = analysis[['required_tasks','completed_required']].fillna(0)\nanalysis['all_required_complete'] = analysis.all_required_complete.fillna(False).astype(bool)\nanalysis = analysis.merge(assign[['merchandiser_id','group']],on='merchandiser_id',how='left',suffixes=('','_assigned'),validate='many_to_one')\n# Assignment ledger is the source of truth for ITT, even if a raw visit label were inconsistent.\nanalysis['group'] = analysis.group_assigned\nanalysis['scheduled_date'] = analysis.scheduled_at.dt.date\nanalysis['phase'] = np.where((analysis.scheduled_at >= '2025-09-15') & (analysis.scheduled_at < '2025-10-25'),'experiment','pre')\nexp = analysis.loc[analysis.phase.eq('experiment')].copy()\nuser_metric = (exp.groupby(['merchandiser_id','group'])\n    .agg(planned_visits=('visit_id','nunique'), successful_visits=('all_required_complete','sum'),\n         completion_rate=('all_required_complete','mean'), visit_minutes=('duration_min','mean'),\n         completed_tasks=('completed_required','sum'), required_tasks=('required_tasks','sum'))\n    .reset_index())\nprint(f'Аналитические визиты в эксперименте: {len(exp):,}; пользователи: {user_metric.merchandiser_id.nunique():,}')\ndisplay(user_metric.groupby('group').agg(users=('merchandiser_id','nunique'),visits=('planned_visits','sum'),mean_user_completion=('completion_rate','mean'),median_visits=('planned_visits','median')))\n"""),
md("""## 5. Проверка рандомизации и pre-period\n\nПроверяем размер групп и баланс предэкспериментальных характеристик. p-value баланса не используется как фильтр эксперимента: случайные отличия возможны, важнее заранее заданная схема рандомизации и масштаб различий.\n"""),
code("""balance = assign.groupby('group').agg(users=('merchandiser_id','nunique'),mean_tenure=('tenure_months','mean')).T\ndisplay(balance)\nfor col in ['city','tenure_band','platform']:\n    print(f'\\n{col} — доли по группе')\n    display(pd.crosstab(assign[col],assign.group,normalize='columns').round(3))\npre = analysis.loc[analysis.phase.eq('pre')].groupby(['merchandiser_id','group']).agg(pre_visits=('visit_id','nunique'),pre_completion=('all_required_complete','mean')).reset_index()\ndisplay(pre.groupby('group').agg(users=('merchandiser_id','nunique'),mean_pre_visits=('pre_visits','mean'),mean_pre_completion=('pre_completion','mean')))\n"""),
md("""## 6. Оценка выборки и мощности\n\nЕдиница выборки — пользователь (мерчендайзер), а не отдельный визит. Для планирования используем стандартное отклонение индивидуальной метрики в pre-period и формулу двух независимых средних при равных группах.\n\nФормула приближённого размера на группу: `n = 2 × (z(1−α/2) + z(power))² × σ² / MDE²`. Это плановая оценка; после эксперимента показываем фактический размер и неопределённость.\n"""),
code("""pre_sd = float(pre.pre_completion.std(ddof=1))\nalpha = 0.05\npower_target = 0.80\nmde = 0.01  # 1 п.п.\nz_alpha = stats.norm.ppf(1-alpha/2)\nz_power = stats.norm.ppf(power_target)\nn_per_arm = math.ceil(2*(z_alpha+z_power)**2 * pre_sd**2 / mde**2)\nusers_per_arm = user_metric.groupby('group').merchandiser_id.nunique()\nprint(f'Pre-period SD пользовательской доли: {pre_sd:.4f}')\nprint(f'Расчётная выборка для MDE={mde:.1%}, alpha={alpha:.2f}, power={power_target:.0%}: {n_per_arm:,} пользователей на группу')\nprint('Фактическая выборка:', users_per_arm.to_dict())\nprint('Достаточно по простому плановому расчёту:', bool((users_per_arm >= n_per_arm).all()))\n"""),
md("""## 7. Основной анализ A/B-теста\n\nПроверяем H₀: Δ = 0 против H₁: Δ ≠ 0. Сначала агрегируем до одного значения на мерчендайзера, затем применяем Welch t-test. ДИ строится для разности средних пользовательских долей.\n"""),
code("""c = user_metric.loc[user_metric.group.eq('control'),'completion_rate'].to_numpy()\nt = user_metric.loc[user_metric.group.eq('treatment'),'completion_rate'].to_numpy()\ndelta = t.mean()-c.mean()\nse = math.sqrt(t.var(ddof=1)/len(t)+c.var(ddof=1)/len(c))\ndf = (t.var(ddof=1)/len(t)+c.var(ddof=1)/len(c))**2 / ((t.var(ddof=1)/len(t))**2/(len(t)-1)+(c.var(ddof=1)/len(c))**2/(len(c)-1))\ntcrit = stats.t.ppf(1-alpha/2,df)\nci = (delta-tcrit*se, delta+tcrit*se)\nwelch = stats.ttest_ind(t,c,equal_var=False)\nsummary = pd.DataFrame({'group':['control','treatment'],'users':[len(c),len(t)],'mean_user_completion':[c.mean(),t.mean()], 'sd_user_completion':[c.std(ddof=1),t.std(ddof=1)]})\ndisplay(summary)\nprint(f'Абсолютный эффект тест − контроль: {delta:+.3%} ({delta*100:+.2f} п.п.)')\nprint(f'95% ДИ: [{ci[0]:+.3%}, {ci[1]:+.3%}]')\nprint(f'Welch t-test: t={welch.statistic:.3f}, df≈{df:.1f}, p-value={welch.pvalue:.4f}')\nprint('Отвергаем H₀ при α=0.05:', bool(welch.pvalue < alpha))\nprint('Достигнут бизнес-MDE (+1 п.п.):', bool(delta >= mde))\n"""),
md("""### Сравнение с наивным визитным тестом\n\nНиже показан обычный z-тест для долей на уровне визитов. Он игнорирует кластеризацию визитов внутри мерчендайдера, поэтому стандартная ошибка может быть занижена. Используем его только для иллюстрации того, почему единица рандомизации должна определять статистический вывод.\n"""),
code("""visit_tab = exp.groupby('group').all_required_complete.agg(['sum','count'])\np0=visit_tab.loc['control','sum']/visit_tab.loc['control','count']; p1=visit_tab.loc['treatment','sum']/visit_tab.loc['treatment','count']\np_pool=(visit_tab['sum'].sum()/visit_tab['count'].sum())\nse_naive=math.sqrt(p_pool*(1-p_pool)*(1/visit_tab.loc['control','count']+1/visit_tab.loc['treatment','count']))\nz_naive=(p1-p0)/se_naive\np_naive=2*stats.norm.sf(abs(z_naive))\nprint('Наивный визитный эффект:',f'{(p1-p0):+.3%}','p-value:',f'{p_naive:.4f}')\nprint('Основной вывод остаётся по user-level Welch test:',f'p={welch.pvalue:.4f}')\n"""),
md("""## 8. Вторичные и защитные метрики\n\nРезультаты вторичных метрик являются поддерживающими. Для множественных сравнений не трактуем отдельные p-value как подтверждающие; при масштабировании эксперимента следует заранее определить семейство гипотез и коррекцию.\n"""),
code("""# Доля eligible-визитов тестовой группы, где лог зафиксировал открытие нового экрана\nexposed_visit_ids=set(events.loc[events.event_name.eq('priority_screen_opened'),'visit_id'])\neligible_treatment_visits=exp.loc[exp.group.eq('treatment') & exp.actual_start_at.notna(),'visit_id'].nunique()\nvisit_exposure_rate=len(exposed_visit_ids)/eligible_treatment_visits\nuser_metric['avg_visit_minutes'] = user_metric.visit_minutes\nsecondary = user_metric.groupby('group').agg(users=('merchandiser_id','nunique'),completion_rate=('completion_rate','mean'),mean_visits=('planned_visits','mean'),mean_visit_minutes=('avg_visit_minutes','mean'),task_completion=('completed_tasks','sum'))\ndisplay(secondary)\nprint(f'Открытие нового экрана на eligible-визитах тестовой группы: {visit_exposure_rate:.1%} ({len(exposed_visit_ids):,}/{eligible_treatment_visits:,})')\n# Cancellation/no-show share is measured on all planned visits\nguard=exp.assign(not_started=exp.actual_start_at.isna(),invalid_duration=exp.invalid_duration)\ndisplay(guard.groupby('group').agg(no_start_rate=('not_started','mean'),invalid_duration_rate=('invalid_duration','mean'),mean_duration_min=('duration_min','mean')))\n"""),
md("""## 9. Сегментный анализ и визуализация\n\nСегменты — разведочный анализ: результаты не доказывают, что эффект различается между сегментами. При принятии решений потребуются заранее заданные interaction-тесты и поправка на множественные сравнения.\n"""),
code("""seg = exp.merge(merch[['merchandiser_id','platform','tenure_band']],on='merchandiser_id',how='left',validate='many_to_one')\nseg_user=seg.groupby(['merchandiser_id','group','city','platform','tenure_band']).all_required_complete.mean().reset_index(name='rate')\nseg_summary=seg_user.groupby(['platform','group']).rate.agg(['mean','count']).unstack('group')\nseg_summary['difference_pp']=(seg_summary[('mean','treatment')]-seg_summary[('mean','control')])*100\ndisplay(seg_summary)\nfig, axes=plt.subplots(1,2,figsize=(12,4))\nmeans=user_metric.groupby('group').completion_rate.mean().reindex(['control','treatment'])\naxes[0].bar(['Control','Treatment'],means.values,color=['#6c8ebf','#4d9b76'])\naxes[0].set_ylim(0,1); axes[0].set_ylabel('Mean user-level completion rate'); axes[0].set_title('Primary outcome')\naxes[1].hist(c,bins=24,alpha=.65,label='Control',color='#6c8ebf',density=True)\naxes[1].hist(t,bins=24,alpha=.55,label='Treatment',color='#4d9b76',density=True)\naxes[1].set_title('User-level outcome distribution'); axes[1].set_xlabel('Completion rate'); axes[1].legend()\nplt.tight_layout()\n"""),
md("""## 10. Интерпретация и рекомендация\n\nИспользуем заранее согласованное правило: масштабирование требует (1) статистически значимого положительного эффекта по основной метрике, (2) эффекта не ниже бизнес-MDE +1 п.п. и (3) отсутствия ухудшения защитных метрик. Иначе — не раскатывать на всех пользователей; оценить доверительный интервал, внедрение и стоимость дополнительного теста.\n"""),
code("""if (welch.pvalue < alpha) and (delta >= mde):\n    decision='Рекомендация: перейти к поэтапному запуску и мониторингу защитных метрик.'\nelif (welch.pvalue < alpha) and (delta < mde):\n    decision='Рекомендация: эффект статистически заметен, но ниже бизнес-MDE; не масштабировать без оценки экономики и продуктовой ценности.'\nelif ci[1] < mde:\n    decision='Рекомендация: не объявлять победителя. Верхняя граница 95% ДИ ниже бизнес-MDE; оставить контроль, если эффект меньше +1 п.п. не оправдывает внедрение.'\nelse:\n    decision='Рекомендация: не объявлять победителя; дополнительный тест имеет смысл, если 95% ДИ всё ещё включает бизнес-MDE.'\nprint(decision)\nprint(f'Δ={delta:+.2%}, 95% ДИ [{ci[0]:+.2%}, {ci[1]:+.2%}], p={welch.pvalue:.4f}; MDE={mde:.1%}.')\n"""),
md("""## 11. Ограничения и следующий эксперимент\n\n- Данные смоделированы; статистический результат демонстрирует метод и не является доказательством для реального продукта.\n- Один сотрудник остаётся единицей анализа; перевод, увольнение или неполное логирование могут привести к missing outcomes и требуют отдельного протокола.\n- Новая версия может менять поведение только у фактически экспонированных пользователей; основной ITT не заменяем post-hoc анализом exposed.\n- Перед реальным запуском зафиксировать метрики, MDE, окно наблюдения, исключения, правила остановки и план множественных сравнений. Проверить SRM по ежедневным назначениям, стабильность логирования, версии приложения и календарные эффекты.\n- Для оценки времени визита использовать заранее определённые правила валидности и устойчивые метрики; здесь duration приведена как защитная диагностика.\n"""),
md("""## 12. Словарь таблиц\n\n- `merchandisers.csv` — характеристики пользователей и команда.\n- `experiment_assignments.csv` — постоянное назначение 1:1 и strata.\n- `visits.csv` — плановые визиты, фактические времена и исходный статус; содержит небольшое количество точных транспортных дублей для практики QA.\n- `tasks.csv` — обязательные задачи в рамках визита и их статусы.\n- `events.csv` — события открытия экранов и визитов.\n- `outlets.csv`, `projects.csv` — справочники торговых точек и проектов-клиентов.\n\nДанные можно пересоздать скриптом `generate_data.py` с фиксированным seed.\n"""),
]
nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3 (ipykernel)','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.9.0'}},'nbformat':4,'nbformat_minor':5}
if not (ROOT/'MAXMERCH_AB_test_analysis.ipynb').exists():
    (ROOT/'MAXMERCH_AB_test_analysis.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')

print(json.dumps({'visits_raw':len(visits),'unique_visits':visits.visit_id.nunique(),'tasks':len(tasks),'events':len(events),'users':len(merch)},indent=2))
