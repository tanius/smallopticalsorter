# Coffee Cobra

**[1. Overview](#1-overview)**<br/>
**[2. Parts](#2-parts)**

* [2.1. Outward Filter](#21-outward-filter)
* [2.2. Strap Extender](#22-strap-extender)

**[3. Todo List](#3-todo-list)**<br/>
**[4. Code Conventions](#4-code-conventions)**<br/>


## 1. Overview

**Description.** An open source and open hardware, small optical sorter for agricultural items like coffee, nuts, corn and similar hard, dry, small items with good flow. The original design is for coffee, but since the design is fully parametric you can calculate a machine for your size of items (say, walnuts).

**Project Resources.**

* **[Project description and forum](https://edgeryders.eu/t/7122).** For announcements, introductions and general discussion. Until we have a project website, this is the "project home".

* **[Code repository](https://github.com/tanius/smallopticalsorter).** Contains all code, CAD designs, and training images.

* **[Dynalist document](https://dynalist.io/d/HNW1DrMNCi6DTKCEL2LFi_uE).** This is the project's one and only collaborative document. It contains all design rationales, part specs, standards used, component documentation, documentation links, development instructions / FAQ, and links to related work.

**Status.** As of 2021-01, this project is in the advanced conceptual stage. The basic machine design is complete and we're now working on CAD drawings, part selection and mechanical manufacturing. A working prototype is expected in 2021-Q2. That will not yet be a machine ready for the general public, but early adopters may already build their own machines then and contribute to further development with initial practical experiences.

**Licence.** This design is licensed under the [Unlicense](https://github.com/tanius/smallopticalsorter/blob/master/LICENSE). Libraries bundled with this repository may use different open source licences, as mentioned in their library files.


## 2. Hardware Build

To generate the geometry of the mechanical parts from the [parametric design code files](https://github.com/tanius/smallopticalsorter/tree/master/mechanics), you need to install [CadQuery](https://github.com/CadQuery/cadquery). Preferably also [CQ-editor](https://github.com/CadQuery/CQ-editor), a Qt based cross-platform user interface for CadQuery.

[TODO]


## 3. Software Installation

There is not yet any machine control software. However, from earlier work there are two documents with installation instructions which may or may not be relevant for the final design:

* [Realtime Linux installation in a Raspberry Pi](https://github.com/tanius/smallopticalsorter/blob/master/doc/rpi_setup.md)
* [Installing the experimental coffee beans classifier](https://github.com/tanius/smallopticalsorter/blob/master/doc/coffee_classifier.md)


## 4. Usage

[TODO]

## 5. Contributor Guide

[TODO]

<!--
### 5.1. Becoming a contributor

### 5.2. Python conventions

### 5.3. C++ conventions
-->
