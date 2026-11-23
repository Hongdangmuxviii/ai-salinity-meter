from pathlib import Path
import re, csv, json, statistics

root=Path(__file__).resolve().parent
raw=(root/'salt_1p1_baseline_raw.txt').read_text(encoding='utf-8-sig')
pattern=r'RESULT temp_C=([\d.]+)\s+response=([\d.]+) / 100\s+D0\+=([\d.]+)\s+D1\+=([\d.]+)\s+range=([\d.]+)\.\.([\d.]+)'
results=[]
for i,m in enumerate(re.finditer(pattern,raw),1):
    v=list(map(float,m.groups()))
    results.append(dict(trial=i,temperature_C=v[0],raw_response=v[1],forward_response=v[2],reverse_response=v[3],pair_min=v[4],pair_max=v[5]))
phases=[];trial=0
for line in raw.splitlines():
    mt=re.search(r'SALT_WATER_TEST .* trial=(\d+)',line)
    if mt:trial=int(mt.group(1))
    m=re.search(r'PHASE (D[01]\+) A0=(-?[\d.]+) A1=(-?[\d.]+) A2=(-?[\d.]+) A3=(-?[\d.]+)',line)
    if not m:continue
    p=m.group(1);a0,a1,a2,a3=map(float,m.groups()[1:])
    probe=a0-a1;drive=a2-a3
    phases.append(dict(trial=trial,phase=p,A0_V=a0,A1_V=a1,A2_V=a2,A3_V=a3,probe_signed_V=round(probe,4),drive_signed_V=round(drive,4),sampled_signs_disagree=probe*drive<0))
assert len(results)==3 and len(phases)==30
for name,rows in [('salt_1p1_summary.csv',results),('salt_1p1_phase_voltages.csv',phases)]:
    with (root/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
tap=json.loads((root/'tap_water_baseline_statistics.json').read_text(encoding='utf-8-sig'))
summary={
    'condition':'salt_water', 'reference_concentration_percent_user_stated':1.1,
    'concentration_method':'separate_salinity_meter_user_confirmed',
    'reference_meter_removed_during_measurement':True,
    'reference_meter_model':None,'reference_meter_calibration_status':None,
    'salt_and_water_mass_g':None,'same_water_batch_as_tap_baseline':None,
    'immersion_depth_mm':None,'raw_is_salinity_percent':False,
    'trials':results,'mean_raw':round(statistics.mean(r['raw_response'] for r in results),4),
    'temperature_mean_C':round(statistics.mean(r['temperature_C'] for r in results),4),
    'tap_baseline_mean_raw':tap['mean_raw'],
    'raw_difference_from_tap':round(statistics.mean(r['raw_response'] for r in results)-tap['mean_raw'],4),
    'sampled_voltage_sign_disagreement_phases':sum(p['sampled_signs_disagree'] for p in phases),
    'total_phases':len(phases),
    'observation':'Trial averages repeat closely, but within-burst pair response increases and D1+ sampled A0-A1 remains positive despite negative A2-A3. A0 and A1 are sequential samples; simultaneous physical probe polarity is not established by this data.',
    'calibration_point_accepted':False,
    'next_check':'Rinse and return to an uncontaminated aliquot of the same tap water, then examine pulse timing, electrode polarization, sequential-sampling effects and wiring before calibration.'
}
(root/'salt_1p1_statistics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['mean_raw','temperature_mean_C','raw_difference_from_tap','sampled_voltage_sign_disagreement_phases','total_phases','calibration_point_accepted']},ensure_ascii=False))
