# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Development tooling: [uv](https://docs.astral.sh/uv/) replaces Poetry. The development tools and Home Assistant are a `dev` dependency group in `pyproject.toml` (the project is not built as a package), and the locked versions are in `uv.lock` (`poetry.lock` is removed). To work on the integration, run `uv sync` instead of `poetry install`. The CI and release workflows use uv. The integration is unchanged.

## [1.3.15a2] - 2026-10-05

### Added

- A GrDF account can be set up from the Home Assistant UI, with a config flow and an options flow for the update interval and the number of days downloaded. The YAML configuration keeps working: it is imported into the UI, and it updates the entry of the same meter while it is there.
- The sensor has a unique ID per meter and belongs to a device.

### Changed

- Upgrade PyGazpar library version to 1.4.0a4.
- Python 3.14.2 or newer is now required for development, and CI runs on Python 3.14.
- Development dependency: Home Assistant `^2026.9.0`.
- Development dependencies: `pytest-homeassistant-custom-component` `0.13.367` runs the config flow tests in a Home Assistant instance; pytest `^9.0.3`, pytest-asyncio `1.4.0` and httpcore `1.0.9` (the version that imports on Python 3.14.7).
- Development tooling: ruff (lint and format) and mypy replace flake8, isort, black and pylint. Ruff and mypy are updated to their latest stable versions, and the CI lint and test steps are inlined in the workflow.
- The sensor is now a `SensorEntity`: its device class, state class and unit are entity properties rather than attributes. The attributes Home Assistant derives from them are unchanged, and the sensor is pushed by each query instead of being polled.

### Removed

- The GRDF username is no longer exposed in the `sensor.gazpar` attributes, so it is no longer stored in the Home Assistant database.

### Fixed

- A daily reading with a missing index or converter factor no longer raises an error when computing the state: the last known state is kept and a warning is logged. A most recent reading without a converter factor falls back to the previous day, as one without an index already did.
- A failed GRDF query no longer blanks the sensor: the data of the last successful query is kept, and the error is still reported in the `errorMessages` attribute.
- The `hourly` attribute keeps only the most recent reading and error messages are cut to 500 characters, so the attributes stay under the 16 KB limit Home Assistant enforces.

### Security

- Locked dependencies updated to fix open Dependabot alerts: aiohttp, Pillow, PyJWT, urllib3, cryptography, anyio, idna, pycares, python-dotenv, uv, mashumaro, requests, pyOpenSSL, orjson and Jinja2.

## [1.3.15a1] - 2026-10-04

### Changed

- Upgrade PyGazpar library version to 1.4.0a3, which brings pydantic as a new dependency.
- Release process: the create-release workflow takes an explicit version, and checks it against the branch, the existing tags and the changelog before anything is changed.
- Release process: the changelog is finalized automatically, and the GitHub release notes come from its section.
- Release process: GitHub releases are created as drafts by default. A dry run option validates and bumps a release without pushing or publishing it.
- Release process: the version bump commit and the tag are pushed together in one atomic push.

### Removed

- GitVersion, its configuration and the version step in CI.

## [1.3.14] - 2026-09-19

### Fixed

[#86](https://github.com/ssenart/home-assistant-gazpar/pull/86): Spurious multi-thousand kWh jumps in the cumulative energy sensor state, caused by a corrupted or not-yet-finalized most recent daily reading being used as-is.

## [1.3.13] - 2025-07-22

### Changed

[#82](https://github.com/ssenart/home-assistant-gazpar/issues/82): Upgrade PyGazpar library version to 1.3.1.

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

[Unreleased]: https://github.com/ssenart/home-assistant-gazpar/compare/1.3.15a2...HEAD
[1.3.15a2]: https://github.com/ssenart/home-assistant-gazpar/compare/1.3.15a1...1.3.15a2
[1.3.15a1]: https://github.com/ssenart/home-assistant-gazpar/compare/1.3.14...1.3.15a1
