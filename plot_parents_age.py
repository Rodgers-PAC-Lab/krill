import colony.models
import pandas
import matplotlib.pyplot as plt

rec_l = []
for litter in colony.models.Litter.objects.select_related(
    'mother', 'father').prefetch_related('mouse_set').all():
    rec_l.append((
        litter.father.dob,
        litter.mother.dob,
        litter.mouse_set.count(),
        litter.dob,
        litter.date_mated))

df = pandas.DataFrame.from_records(rec_l, columns=(
    'fdob', 'mdob', 'npups', 'pdob', 'dmated'))
df['age'] = (df['pdob'] - df['mdob']).astype('timedelta64[D]')
df['fage'] = (df['pdob'] - df['fdob']).astype('timedelta64[D]')
df['latency'] = (df['pdob'] - df['dmated']).astype('timedelta64[D]')
df['agebin'] = pandas.cut(df['age'], 20, labels=False)
df['fagebin'] = pandas.cut(df['fage'], 20, labels=False)

# group by mother and father age
gobj = df.groupby('agebin')
xax = gobj['age'].mean().values
fgobj = df.groupby('fagebin')
fxax = fgobj['fage'].mean().values

f, axa = plt.subplots(1, 2, figsize=(12, 5), sharex=True, sharey=True)
ax = axa[0]
ax.plot(xax, gobj['npups'].mean().values, label='npups')
ax.plot(xax, gobj['npups'].count().values, label='nlitters')
ax.plot(xax, gobj['latency'].mean().values, label='latency')
ax.set_xlabel("mother's age")
ax.legend()

ax = axa[1]
ax.plot(fxax, fgobj['npups'].mean().values, label='npups')
ax.plot(fxax, fgobj['npups'].count().values, label='nlitters')
ax.plot(fxax, fgobj['latency'].mean().values, label='latency')
ax.set_xlabel("father's age")
ax.legend()

plt.show()