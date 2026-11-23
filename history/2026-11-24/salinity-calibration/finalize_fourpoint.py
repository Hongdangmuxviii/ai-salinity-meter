"""Use all supplied reference concentrations without imposing a two-point shape."""
import csv,json,re
from pathlib import Path
from statistics import median

root=Path(__file__).resolve().parent
archive=Path(r'C:\Users\Yeon\Documents\Codex\2026-11-23\sensor-recheck\diagnostic')
two=json.loads((root/'calibration_model.json').read_text(encoding='utf-8'))
(root/'two_point_draft_not_deployed.json').write_text(json.dumps(two,indent=2),encoding='utf-8')
trials=list(csv.DictReader((archive/'current_ratio_reanalysis_trials.csv').open(encoding='utf-8-sig')))
nodes=[]
for condition,percent in [('original_0p5',0.5),('original_1p1',1.1)]:
    rows=[r for r in trials if r['condition']==condition]
    nodes.append(dict(reference_percent=percent,index=median(float(r['current_index']) for r in rows),
                      temperature_C=median(float(r['temperature_C']) for r in rows),
                      source=rows[0]['source'],source_kind='archived_reprocessed',
                      trial_indices=[float(r['current_index']) for r in rows]))
for key in ('low','high'):
    node=two[key].copy();node['source_kind']='fresh_k';nodes.append(node)
nodes.sort(key=lambda n:n['reference_percent'])
if not all(nodes[i]['index']<nodes[i+1]['index'] for i in range(3)):
    raise ValueError('Nonmonotonic calibration references')
model=dict(id='REF_4P_20261124_V1',kind='monotonic piecewise-linear empirical lookup',
           nodes=nodes,aggregation='median of3 identical raw-current acquisitions',
           response_formula='C=200*(A1-A3)/(A2-A3)',A0_in_calculation=False,
           temperature_compensated=False,accuracy_independently_validated=False,
           reference_meter_calibration_traceability='not supplied',
           scope='Comparative prototype calibration0.5..2.0%; archive0.5/1.1 plus fresh0.6/2.0 references. Recorded temperature conditions differ; no complete temperature correction or independent accuracy claim.')
(root/'calibration_model.json').write_text(json.dumps(model,indent=2),encoding='utf-8')
with (root/'calibration_references.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['reference_percent','response_index_median','temperature_C','source_kind','source'])
    writer.writeheader()
    for n in nodes:writer.writerow(dict(reference_percent=n['reference_percent'],response_index_median=n['index'],temperature_C=n['temperature_C'],source_kind=n['source_kind'],source=n['source']))
sketch=root/'SalinityMeterCalibrated'
header='''#pragma once
// Comparative prototype table; independent accuracy and temperature correction are not validated.
constexpr char calibrationId[] = "REF_4P_20261124_V1";
constexpr unsigned int calibrationPointCount = 4;
'''
for name,field in [('calibrationIndices','index'),('calibrationPercents','reference_percent'),('calibrationTemperatures','temperature_C')]:
    header+=f'constexpr double {name}[4] = {{'+', '.join(f'{n[field]:.12g}' for n in nodes)+'};\n'
header+='constexpr double calibrationIndexLow = calibrationIndices[0];\nconstexpr double calibrationIndexHigh = calibrationIndices[3];\n'
(sketch/'CalibrationTable.h').write_text(header,encoding='utf-8')
path=sketch/'SalinityMeterCalibrated.ino'
src=path.read_text(encoding='utf-8')
start=src.index('void printCalibration() {')
end=src.index('\nvoid runCalibratedMeasurement() {',start)
replacement='''double interpolateCalibration(double index) {
  unsigned int segment=0;
  while (segment<calibrationPointCount-2 && index>calibrationIndices[segment+1]) ++segment;
  const double x0=calibrationIndices[segment], x1=calibrationIndices[segment+1];
  const double y0=calibrationPercents[segment], y1=calibrationPercents[segment+1];
  return y0+(index-x0)*(y1-y0)/(x1-x0);
}

void printCalibration() {
  Serial.printf("CAL_TABLE id=%s points=4 aggregation=median3 temperature_compensated=false accuracy_independently_validated=false\\n",calibrationId);
  for (unsigned int i=0;i<calibrationPointCount;++i)
    Serial.printf("CAL_POINT i=%u reference_percent=%.1f response_index=%.8f reference_temp_C=%.2f\\n",i,calibrationPercents[i],calibrationIndices[i],calibrationTemperatures[i]);
}
'''
src=src[:start]+replacement+src[end:]
src=src.replace('  const double proxy=index/(100.0-index);\n  const double estimatedPercent=calibrationGain*proxy+calibrationOffset;',
                '  const double estimatedPercent=interpolateCalibration(index);')
src=src.replace('SALINITY_CAL_2P_V1','SALINITY_CAL_4P_V1').replace('estimate_percent=%.3f','estimate_percent=%.2f')
if 'calibrationGain' in src or 'calibrationOffset' in src:raise ValueError('Old fit remains')
path.write_text(src,encoding='utf-8')
# Table round-trip and monotonicity are numeric checks, not an accuracy study.
def estimate(x):
    s=0
    while s<2 and x>nodes[s+1]['index']:s+=1
    a,b=nodes[s],nodes[s+1]
    return a['reference_percent']+(x-a['index'])*(b['reference_percent']-a['reference_percent'])/(b['index']-a['index'])
assert all(abs(estimate(n['index'])-n['reference_percent'])<1e-10 for n in nodes)
grid=[nodes[0]['index']+(nodes[-1]['index']-nodes[0]['index'])*i/100 for i in range(101)]
assert all(estimate(grid[i])<estimate(grid[i+1]) for i in range(100))
print(json.dumps(model,indent=2))
