# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - 2021-11-20

### Changed
- Upgrade Netatmo component as available in Home Assistant version 2021.11.5.
- [PresenceCamera] Permit to stream images even if cameras are off.

## [0.2.2] - 2021-07-23

### Fixed
- Add Netatmo component version in manifest file (required for custom_components).

## [0.2.1] - 2021-07-21

### Changed
- Upgrade Netatmo component as available in Home Assistant version 2021.7.3.
- [PresenceCamera] Permit to stream images even if cameras are off.

### Fixed
- Fix 'gazpar module not found' error after upgrading HA version to latest.

## [0.2.0] - 2021-04-21

### Requires PyGazpar >= 0.2.0

### Added
- Be able to retrieve consumption not only on a daily basis, but weekly and monthly. New entity names:
    - sensor.gazpar_daily_energy
    - sensor.gazpar_weekly_energy
    - sensor.gazpar_monthly_energy

- All the entity detail values are available in entity attributes.

Daily example:
```yaml
attribution: Data provided by GrDF
username: stephane.senart@gmail.com
time_period: 19/04/2021
start_index_m3: 13708
end_index_m3: 13713
volume_m3: 4.7
energy_kwh: 52
converter_factor_kwh/m3: 11.268
temperature_degC: 12
type: MES
timestamp: 2021-04-21T07:50:09.505625
unit_of_measurement: kWh
friendly_name: Gazpar daily energy
icon: mdi:fire
```

Weekly example:
```yaml
attribution: Data provided by GrDF
username: stephane.senart@gmail.com
current: 
  time_period: Du 19/04/2021 au 19/04/2021
  volume_m3: 4.7
  energy_kwh: 52
  timestamp: '2021-04-21T07:54:06.324645'

previous: 
  time_period: Du 12/04/2021 au 18/04/2021
  volume_m3: 57.1
  energy_kwh: 643
  timestamp: '2021-04-21T07:54:06.324645'

unit_of_measurement: kWh
friendly_name: Gazpar weekly energy
icon: mdi:fire
```

Monthly example:
```yaml
attribution: Data provided by GrDF
username: stephane.senart@gmail.com
current: 
  time_period: Avril 2021
  volume_m3: 135.4
  energy_kwh: 1525
  timestamp: '2021-04-21T07:58:01.392893'

previous: 
  time_period: Mars 2021
  volume_m3: 261.1
  energy_kwh: 2937
  timestamp: '2021-04-21T07:58:01.392893'

unit_of_measurement: kWh
friendly_name: Gazpar monthly energy
icon: mdi:fire
```

- Be able to test using offline data. A new configuration parameter 'test_mode' is available to switch in that test mode:
```yaml
sensor:
  - platform: gazpar
    username: !secret gazpar.username
    password: !secret gazpar.password
    webdriver: /config/drivers/geckodriver
    tmpdir: /config/tmp
    wait_time: 30
    scan_interval: 01:00:00
    test_mode: False
```

### Removed
The previous entity names have been removed:
- sensor.gazpar_last_period_start_time
- sensor.gazpar_last_period_end_time
- sensor.gazpar_last_start_index
- sensor.gazpar_last_end_index
- sensor.gazpar_last_energy
- sensor.gazpar_last_volume
- sensor.gazpar_last_temperature
- sensor.gazpar_last_converter_factor

However, if for compatibility purpose, you want to keep them, use the following HA template:

```yaml
- platform: template
  sensors:
    gazpar_last_period_start_time:
      friendly_name: "Gazpar last period start time"    
      value_template: "{{ state_attr('sensor.gazpar_daily_energy', 'time_period') }}"
      icon_template: mdi:fire
    gazpar_last_period_end_time:
      friendly_name: "Gazpar last period end time"    
      value_template: "{{ state_attr('sensor.gazpar_daily_energy', 'time_period') }}"
      icon_template: mdi:fire
    gazpar_last_start_index:
      friendly_name: "Gazpar last start index"
      unit_of_measurement: 'm³'      
      value_template: "{{ state_attr('sensor.gazpar_daily_energy', 'start_index_m3') | float }}"
      icon_template: mdi:fire      
    gazpar_last_end_index:
      friendly_name: "Gazpar last end index"
      unit_of_measurement: 'm³'      
      value_template: "{{ state_attr('sensor.gazpar_daily_energy', 'end_index_m3') | float }}"
      icon_template: mdi:fire      
    gazpar_last_volume:
      friendly_name: "Gazpar last volume"
      unit_of_measurement: 'm³'      
      value_template: "{{ state_attr('sensor.gazpar_daily_energy', 'volume_m3') | float }}"
      icon_template: mdi:fire      
    gazpar_last_energy:
      friendly_name: "Gazpar last energy"
      unit_of_measurement: 'kWh'      
      value_template: "{{ state_attr('sensor.gazpar_daily_energy', 'energy_kwh') | float }}"  
      icon_template: mdi:fire
    gazpar_last_converter_factor:
      friendly_name: "Gazpar last converter factor"
      unit_of_measurement: 'kWh/m³'      
      value_template: "{{ state_attr('sensor.gazpar_daily_energy', 'converter_factor_kwh/m3') | float }}"
      icon_template: mdi:fire
    gazpar_last_temperature:
      friendly_name: "Gazpar last temperature"
      unit_of_measurement: '°C'      
      value_template: "{{ state_attr('sensor.gazpar_daily_energy', 'temperature_degC') | float }}"
      icon_template: mdi:fire      
```
