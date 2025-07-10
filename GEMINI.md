I need to restructure my Flask application to handle math lessons more effectively. Here are the key components:

Current Files:

Main app: @app.py

Lesson templates: @templates/grade_7/maths/chapter_1/ (contains individual lesson HTML files)

Main math template: @templates/maths.html

Data source: @static/data/grade7_math.json

Desired Functionality:

When users view maths.html, they should see links to individual lesson pages rather than modal popups

The modal functionality should only appear when viewing a specific lesson

Currently focusing on Chapter 1 implementation

Required Changes:

Modify maths.html to display lesson links instead of modal triggers

Ensure each lesson in chapter_1 can display its content with modal functionality

Update app.py routing to handle:

Listing all lessons (main math page)

Displaying individual lessons

Use grade7_math.json as the data source for lesson content

Structure Guidelines:

Main math page (maths.html) should:

Show chapter/lesson structure

Link to individual lesson pages

Lesson pages should:

Display full lesson content

Include modal functionality for interactive elements

Maintain consistent navigation

Focus Area:

Implement this first for Chapter 1 as a model

Ensure the solution is scalable for additional chapters

Technical Requirements:

Proper Flask routing for the new structure

Jinja templating that works with the nested directory structure

Clean separation between presentation and data