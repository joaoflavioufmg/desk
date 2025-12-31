---
title: "DESK: A Replication- and Experimental-Design-Oriented Framework for Discrete-Event Simulation"
tags:
  - discrete-event simulation
  - simulation experiments
  - replication analysis
  - factorial design
  - reproducible research
  - operations research
authors:
  - name: "João Flávio de Freitas Almeida"
    orcid: 0000-0002-3884-217X
    affiliation: 1
affiliations:
  - name: Graduate Program in Production Engineering (PPGEP), Federal University of Minas Gerais (UFMG), Brazil
    index: 1
date: 2025
bibliography: paper.bib
---

# Summary

Discrete-event simulation (DES) is a widely adopted methodology for the analysis of complex stochastic systems in operations research, logistics, healthcare, and service systems [@banks2010discrete; @law2015simulation]. While mature simulation engines exist for model execution, researchers and students frequently face recurring challenges related to experiment design, replication management, and systematic result aggregation. These methodological steps are often implemented in an ad hoc manner, reducing reproducibility and increasing development effort [@stodden2016reproducibility].

DESK (Discrete Event Simulation Kit) is an open-source framework designed to support the *experimental workflow* of discrete-event simulation studies. Rather than focusing solely on model execution, DESK provides explicit abstractions for replication analysis, factorial and scenario-based experiments, and automated aggregation of performance metrics. The framework promotes reproducible and transparent simulation studies and is suitable for both research and teaching applications.

# Statement of Need

Simulation-based studies typically require multiple replications, parameter variations, and statistical analysis of outputs to ensure valid inference [@law2015simulation; @kleijnen2015design]. Despite their central role in scientific studies, these experimental components are rarely treated as first-class entities in simulation software. As a result, researchers frequently reimplement replication loops, parameter sweeps, and result aggregation logic across projects, increasing the risk of errors and limiting reproducibility [@banks2010discrete].

DESK addresses this gap by structuring simulation experiments as configurable and reusable software components. The framework separates model logic from experimental design, enabling systematic replication analysis and factorial experiments without modifying core simulation code. This approach supports reproducible research practices [@stodden2016reproducibility] and lowers the barrier for conducting rigorous simulation experiments, particularly in academic and educational contexts.

# Related Work

Several established tools support discrete-event simulation, including open-source libraries such as SimPy [@matloff2008introduction], commercial simulation platforms, and domain-specific simulators. These tools provide robust mechanisms for event scheduling and process interaction but typically leave experiment orchestration, replication management, and experimental design to the user.

DESK is designed to complement existing simulation engines by focusing on the organization and execution of simulation experiments rather than on simulation performance or low-level execution mechanisms. Its design is aligned with established principles for the design and analysis of simulation experiments [@kleijnen2015design], while remaining interoperable with existing DES modeling approaches.

# Software Description

DESK is implemented in Python and follows a modular architecture that separates simulation models, experimental configuration, and analysis, in line with best practices in simulation modeling [@law2015simulation].

## Core Architecture

The framework provides:
- A simulation model abstraction for managing entities, resources, and event scheduling
- Modular building blocks for common simulation activities (e.g., creation, processing, and disposal)
- Centralized event logging to support post-simulation analysis and validation

This structure supports model transparency and facilitates verification and validation activities recommended in the simulation literature [@banks2010discrete].

## Replication Framework

DESK includes a replication framework that automates the execution of multiple simulation runs with controlled random seeds, warm-up periods, and simulation horizons. Results from individual replications are aggregated into structured data objects suitable for statistical analysis, following established guidelines for output analysis in simulation studies [@law2015simulation; @kleijnen2015design].

## Factorial and Scenario Analysis

The framework supports factorial experiments by allowing users to define factors, levels, and parameter paths. DESK automatically generates experimental configurations, executes replications for each scenario, and provides tools for analyzing main and interaction effects. This functionality directly supports classical and modern approaches to the design and analysis of simulation experiments [@montgomery2017design; @kleijnen2015design].

# Illustrative Example

An illustrative example included in the repository models a simplified hospital emergency department, a canonical application domain for discrete-event simulation [@law2015simulation]. Patient arrivals, resource constraints, and service processes are represented using DESK building blocks. Replication analysis and factorial experiments are used to evaluate system performance under different arrival rates and staffing levels, demonstrating how DESK enables systematic experimentation without altering the underlying model logic.

# Quality Control

DESK follows open-source best practices for research software development. The repository includes automated tests, example models, and continuous integration workflows to support code reliability. Comprehensive documentation and usage examples are provided to facilitate adoption by both researchers and students. These practices are consistent with current recommendations for reproducible computational research [@stodden2016reproducibility].

# Availability

DESK is released under the GNU General Public License v3.0 and is openly developed on GitHub. The software is archived with a persistent DOI via Zenodo to support citation and long-term accessibility, consistent with open science and research software dissemination practices [@stodden2016reproducibility].

# Acknowledgements

The author acknowledges the Graduate Program in Production Engineering (PPGEP) at the Federal University of Minas Gerais (UFMG) for academic support and the open-source simulation community for foundational tools and inspiration.

# References
