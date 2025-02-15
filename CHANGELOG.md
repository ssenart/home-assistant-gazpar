# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.12] - 2025-02-15

### Changed

[#75](https://github.com/ssenart/home-assistant-gazpar/issues/75): Upgrade PyGazpar library version to 1.3.0.

[#76](https://github.com/ssenart/home-assistant-gazpar/issues/76): Move to Poetry dependency/package management tool.

## [1.3.11] - 2024-12-09

### Fixed
[#72](https://github.com/ssenart/home-assistant-gazpar/issues/72): Fatal error if GrDF returns no start index/end index/volume/energy data in the record.

## [1.3.10] - 2024-10-09

### Fixed
[#63](https://github.com/ssenart/home-assistant-gazpar/issues/63): "UserWarning: Boolean Series key will be reindexed to match DataFrame index" avec la version 1.3.9.

## [1.3.9] - 2024-10-07

### Fixed
[#62](https://github.com/ssenart/home-assistant-gazpar/issues/62): An unexpected error occured while loading the data.

## [1.3.8] - 2024-10-07

### Fixed
[#62](https://github.com/ssenart/home-assistant-gazpar/issues/62): An unexpected error occured while loading the data.

## [1.3.7] - 2024-10-05

## Changed

[#60](https://github.com/ssenart/home-assistant-gazpar/issues/60): [PyGazpar] Upgrade to version 1.2.3.

## [1.3.6] - 2024-09-28

### Fixed

[#52](https://github.com/ssenart/home-assistant-gazpar/issues/52): Error but everything seems ok in config.

## [1.3.5] - 2024-05-08

### Changed

[#36](https://github.com/ssenart/home-assistant-gazpar/issues/36): [PyGazpar] Upgrade to version 1.2.2.

### Added

[#35](https://github.com/ssenart/home-assistant-gazpar/issues/35): [Feature] Renseigner plusieurs PCE.

### Fixed

[#39](https://github.com/ssenart/home-assistant-gazpar/issues/39): [Bug] Error message from PyGazpar is not displayed correctly in the log file.

## [1.3.4] - 2022-12-16

### Changed

[#31](https://github.com/ssenart/home-assistant-gazpar/issues/31): [Feature] For Weekly readings, provide data on the last 10 weeks VS the same weeks one year before.

[#30](https://github.com/ssenart/home-assistant-gazpar/issues/30): Upgrade PyGazpar to version 1.2.0.

[#27](https://github.com/ssenart/home-assistant-gazpar/issues/27): [Issue] Energy Dashboard - Unit error - Regression in HA 2022.11.

### Fixed
[#24](https://github.com/ssenart/home-assistant-gazpar/issues/24): [Bug] gas_energy not showing in the energy dashboard

[#28](https://github.com/ssenart/home-assistant-gazpar/issues/28): [Issue] No data update - GrDF web site is half broken - Download button does not work anymore.

## [1.3.3] - 2022-11-26

### Fixed
[#25](https://github.com/ssenart/home-assistant-gazpar/issues/25): [Bug] Error logged while HA is initializing.

[#24](https://github.com/ssenart/home-assistant-gazpar/issues/24): [Bug] gas_energy not showing in the energy dashboard.

## [1.3.2] - 2022-11-23

### Changed
[#11](https://github.com/ssenart/home-assistant-gazpar/issues/11): Lack of precision.

## [1.3.1] - 2022-11-16

### Changed
[#20](https://github.com/ssenart/home-assistant-gazpar/issues/20): Upgrade PyGazpar to version 1.1.6.

## [1.3.0] - 2022-10-16

### Added
[#14](https://github.com/ssenart/home-assistant-gazpar/issues/14): [Feature] Add attribute 'version' to give the version number of the Gazpar Integration component.

[#13](https://github.com/ssenart/home-assistant-gazpar/issues/13): [Feature] Add attribute errorMessages that displays all error messages raised while using PyGazpar library.

[#12](https://github.com/ssenart/home-assistant-gazpar/issues/12): [Feature] Compute Yearly data from Monthly data.

## [1.2.0] - 2022-10-09

### Added
[#8](https://github.com/ssenart/home-assistant-gazpar/issues/8): Add support for lovelace card. Now, the integration provide a single entity sensor.gazpar that contains both daily, weekly and monthly data.

## [1.1.5] - 2022-07-11

### Fixed
[#9](https://github.com/ssenart/home-assistant-gazpar/issues/9): HTTP Error 500 (Upgrade PyGazpar to 1.1.5).

## [1.1.4.2] - 2022-01-26

### Fixed
Anonymize the README.

## [1.1.4.1] - 2022-01-26

### Fixed
[#2](https://github.com/ssenart/home-assistant-gazpar/issues/2): Usage of device_state_attributes() method is deprecated in Home Assistant 2021.12.

## [1.1.4] - 2022-01-18

### Changed
- Upgrade PyGazpar to 1.1.4.

## [1.1.2] - 2022-01-09

### Changed
- Upgrade PyGazpar to 1.1.2.

### Added
- Add HACS support.
