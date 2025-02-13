# Organization Accountability Project: Tax Expenditure Tracking
==============================================================

## Overview
-----------

Our team has developed the Organization Accountability Project, focusing on creating a transparent and confidential tax expenditure tracking system. This is achieved by leveraging the publicly accessible and immutable ledger: XRP Ledger. This project consists of two main portals: a **Tax Payment Portal** and a **Gov-Spending Tracker Portal**. Our system ensures the privacy of individual transactions using differential privacy, while making the allocation of funds from the government pool publicly accessible. A graph based view is used to track how money moves from source to the vendors(paid by the government).

## Tech Stack
-----------
<a href='https://xrpl.org/' target="_blank"><img alt='XRPL' src='https://img.shields.io/badge/XRPL-100000?style=for-the-badge&logo=XRPL&logoColor=0884FF&labelColor=0884FF&color=0884FF'/></a>&nbsp;&nbsp;&nbsp;&nbsp; <a href='https://container-registry.oracle.com/ords/f?p=113:10::::::' target="_blank"><img alt='Oracle' src='https://img.shields.io/badge/Oracle_CI/CR-100000?style=for-the-badge&logo=Oracle&logoColor=FF0505&labelColor=FF0505&color=FF0505'/></a>&nbsp;&nbsp;&nbsp;&nbsp;<a href='https://www.python.org/' target="_blank"><img alt='' src='https://img.shields.io/badge/Python-100000?style=for-the-badge&logo=&logoColor=9AFF02&labelColor=9AFF02&color=9AFF02'/></a>

## Features
------------

### 1. Tax Payment Portal

- **Income Entry**: Users can input the amount of taxes they pay.
- **Confidential Transactions**: All transactions from users are processed using differential privacy to protect individual financial information.
- **Government Pool**: All funds collected are pooled together, ensuring that individual contributions remain confidential.

### 2. Gov-Spending Tracker Portal

- **Public Allocation**: The distribution of funds from the government pool to various development projects is made publicly available.
- **Project Tracking**: Users can view where their taxes are being allocated, focusing on state, local, or federal development projects.
- **Transparency**: Our system provides clear insights into government spending, enhancing accountability and transparency.

### Privacy and Security

- **Differential Privacy**: We ensure that individual transactions are protected and cannot be reverse-engineered to identify specific users.
- **Public Data**: Only the aggregated funds and their allocations are publicly visible, maintaining the privacy of individual contributors.

### Focus

- **State, Local, and Federal Projects**: Our system is designed to track expenditures on development projects at these levels, excluding larger agencies like the FBI, CIA, and NSA.
- **Dual Currency Support**: The system accommodates both traditional currency and digital coins, though the coins themselves do not hold intrinsic value within the system.

## Goals
--------

- **Enhance Transparency**: We aim to provide citizens with a clear view of how their taxes are being used.
- **Protect Privacy**: We safeguard individual financial information through differential privacy.
- **Promote Accountability**: We encourage responsible government spending by making allocations publicly accessible.

## Usage
-----

We intend for this project to be used by individuals and government entities seeking to improve transparency and accountability in tax expenditure tracking. It offers a unique blend of privacy protection and public oversight, making it suitable for state, local, and federal development projects.


## Accountability Framework
-------------------------

Our project is built around an accountability framework that ensures:

- **Transparency in Spending**: Clear visibility into how funds are allocated.
- **Public Oversight**: Citizens can monitor and provide feedback on government spending.
- **Responsible Governance**: Encourages government entities to manage funds responsibly and efficiently.

## Accessible Portals
-------------------

- **Admin Portal**: Accessible for administrative tasks and oversight.
- **Transaction Portal**: Accessible for users to file their taxes.
- **Financial transaction Visualizer**: Accessible for users to keep a track of where the tax money is being disbursed.
  
## Demo
-------------------
![WhatsApp Image 2025-02-08 at 16 56 03_e462920b](https://github.com/user-attachments/assets/9132085c-70c6-4aed-a875-9cd888838404)

![WhatsApp Image 2025-02-08 at 16 56 03_04a0ea07](https://github.com/user-attachments/assets/1d000f57-da90-453a-b9a2-802fb075ae01)

![WhatsApp Image 2025-02-08 at 16 56 04_f7d37407](https://github.com/user-attachments/assets/e457ab64-c34b-4c19-980e-56a3e07945cb)


## Installation and Running Instructions
-------------------
To run the Organization Accountability Project, follow these steps:

### Step 1: Install Requirements

Ensure you have a `requirements.txt` file with the following content:

```
Flask==3.1.0
xrpl-py==4.0.0
python-dotenv==1.0.1
Werkzeug==3.1.3
```

Run the following command in your terminal:

```
pip install -r requirements.txt
```

### Step 2: Run the Application

Execute the application using Python:

```
python3 app.py
```

### Step 3: Access the Application

Open a web browser and navigate to:

```
http://127.0.0.1:6969
```
### You can also view this hosted on 

```
http://transparenx.co/
```
## Team Contribution
Our team has worked collaboratively to design and implement this system, ensuring that it meets the highest standards of privacy, security, and transparency. We are committed to ongoing development and improvement to ensure the system remains effective and user-friendly.
