**NOTE**

This is a mirror of a GitLab repository.

<p align="center">
<img src="https://i.imgur.com/dX0oq2O.png" width="160" height="160" alt="Dryvo">

<h1 align="center">Dryvo</h1>
</p>

Dryvo is a unique solution for the driving lessons industry. Our aim is to save the teacher’s time and to increase revenues, and for the students to have control on the entire process. Dryvo is changing the way driving lessons are being managed.

## The problem

Teachers spend most of their time dealing with phone calls from students, scheduling lessons and planning their routes and topics for each student. Students are having a hard time keeping track of their payments, lessons, and progress. They usually have no idea when they are ready for a driving test or what topics they will be learning next.

## The solution

Dryvo is a platform for driving lessons scheduling and management. We aim for teachers and students to have control on the entire process - from co-scheduling lessons to tracking payments and topics. Students can track their progress, see what topics they have learned and control their payment balance. Teachers, on the other hand, can focus on each lesson without having to worry about scheduling lessons or dealing with payments ahead.
In addition to the easier interaction service we offer, we plan on adding many more features - smart lessons scheduler, where the machine will know the teacher preferences and can automatically decide lesson times. Moreover, an efficient route-planner so the teacher can save valuable time and cut on gas expenses.

### Key features

-   Smart scheduling by:
    -   Student & appointments locations
    -   Traffic and arrivals time
    -   Student requirements
    -   Internal rules taught by dozens of teachers
    -   Teacher work days
-   Lesson tracking
-   Payments tracking
-   Lesson topics
-   PDF reports for students
-   Teacher reviews

## Installation

Dryvo can be installed using `pip` similar to other Python packages. If you want to use the PDF reporting feature, you would have to install [Weasyprint](https://weasyprint.readthedocs.io/en/stable/install.html).

```bash
$ pip install .
```
   
Or with installing the tests requirements:

```bash
$ pip install .[test]
```


## Getting Started

```bash
$ flask run
```

Dryvo uses [Flask](https://github.com/pallets/flask) as a web framework, therefore running the app is the same as any other Flask app. If you want to use a production server such as `gunicorn`, you can use the command below:

```bash
$ gunicorn --preload --chdir ./server "app:create_app()"
```


### Running tests

```bash
$ python run -m pytest
```

### Structure Explanation

```
├── LICENSE
├── Procfile
├── README.md
├── logs
├── messages.pot
├── migrations - Database migrations using Alembic
├── server
│   ├── __init__.py
│   ├── api - Everything regarding the API endpoints
│   │   ├── __init__.py
│   │   ├── babel.py
│   │   ├── blueprints - Flask blueprints, endpoints divided by logic
│   │   ├── database
│   │   │   ├── __init__.py
│   │   │   ├── consts.py
│   │   │   ├── database.py
│   │   │   ├── mixins.py
│   │   │   ├── models - Database models, where each file is essentialy a table
│   │   │   └── utils.py
│   │   ├── gmaps.py - Google Maps integration
│   │   ├── push_notifications.py
│   │   ├── rules - Custom student rules for scheduling
│   │   ├── social - Social networks integration
│   │   └── utils.py
│   ├── app.py - Main entry point for the application
│   ├── app_config.py
│   ├── babel.cfg
│   ├── consts.py
│   ├── error_handling.py
│   ├── extensions.py
│   ├── static
│   ├── templates - PDF reports templates (HTML)
│   │   └── reports
│   └── translations
├── setup.cfg
├── setup.py
└── tests
```

