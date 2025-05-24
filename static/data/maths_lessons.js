// curriculumLoader.js
document.addEventListener('DOMContentLoaded', function() {
    // Get the grade and subject from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const grade = urlParams.get('grade');
    const subject = urlParams.get('subject');

    // Determine which JSON file to load based on parameters
    const jsonFile = `data/${grade}_${subject.toLowerCase()}.json`;

    // Fetch the JSON data
    fetch(jsonFile)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Render the page with the fetched data
            renderCurriculumPage(data);
        })
        .catch(error => {
            console.error('Error loading curriculum data:', error);
            // Fallback to a default page or show error message
            document.getElementById('main-content').innerHTML = `
                <div class="alert alert-danger">
                    <h4>Error Loading Content</h4>
                    <p>Unable to load the ${grade} ${subject} curriculum. Please try again later.</p>
                    <a href="/" class="btn btn-outline-danger">Return Home</a>
                </div>
            `;
        });

    // Function to render the page with curriculum data
    function renderCurriculumPage(subjectData) {
        // Set the page title
        document.title = subjectData.title || `${subjectData.grade} ${subjectData.subject}`;

        // Progress data (would normally come from user's profile)
        const progress = calculateUserProgress(); // This would be a function that checks user progress

        // Render the hero section
        const heroSection = document.querySelector('.hero-section');
        if (heroSection && subjectData.hero_image) {
            heroSection.style.background = `
                linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)),
                url('${subjectData.hero_image}')
            `;
        }

        // Update hero content
        updateElementText('.hero-section .display-3', `${subjectData.grade} <span class="text-warning">${subjectData.subject}</span>`);
        updateElementText('.hero-section .lead', subjectData.tagline);
        updateElementIcon('.hero-section .display-1', subjectData.icon);

        // Update course overview
        updateElementText('.course-overview h2', `${subjectData.grade} ${subjectData.subject} Curriculum`);
        updateElementText('.course-overview .lead', subjectData.description);
        
        // Update domains list
        const domainsList = document.querySelector('.course-overview .list-group');
        if (domainsList) {
            domainsList.innerHTML = subjectData.domains.map(domain => 
                `<li class="list-group-item bg-light">
                    <i class="bi bi-check-circle-fill text-success me-2"></i>${domain}
                </li>`
            ).join('');
        }

        // Update feature note
        updateElementText('.course-overview .alert', `
            <i class="bi bi-lightbulb-fill me-2"></i>${subjectData.feature_note}
        `);

        // Update course stats
        updateElementText('.course-stats .badge:nth-child(1)', subjectData.stats.total_lessons);
        updateElementText('.course-stats .badge:nth-child(2)', subjectData.stats.video_hours);
        updateElementText('.course-stats .badge:nth-child(3)', subjectData.stats.practice_problems);
        updateElementText('.course-stats .badge:nth-child(4)', subjectData.stats.assessments);

        // Update progress bar if user is logged in
        if (typeof userLoggedIn !== 'undefined' && userLoggedIn) {
            document.querySelector('.progress-bar').style.width = `${progress}%`;
            document.querySelector('.progress-bar').setAttribute('aria-valuenow', progress);
            document.querySelector('.progress-percent').textContent = `${progress}%`;
        } else {
            document.querySelector('.progress-container').style.display = 'none';
        }

        // Render units and lessons
        const accordion = document.getElementById('lessonsAccordion');
        if (accordion) {
            accordion.innerHTML = subjectData.units.map((unit, index) => `
                <div class="accordion-item mb-3 border-${unit.color}">
                    <h2 class="accordion-header">
                        <button class="accordion-button bg-${unit.color} ${unit.color === 'warning' ? 'text-dark' : 'text-white'} fw-bold collapsed" 
                                type="button" data-bs-toggle="collapse" 
                                data-bs-target="#unit${index + 1}" 
                                aria-expanded="false" 
                                aria-controls="unit${index + 1}">
                            Unit ${index + 1}: ${unit.title}
                        </button>
                    </h2>
                    <div id="unit${index + 1}" class="accordion-collapse collapse" data-bs-parent="#lessonsAccordion">
                        <div class="accordion-body">
                            <div class="list-group">
                                ${unit.lessons.map(lesson => `
                                    <a href="${lesson.link || '#'}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                                        <div>
                                            <i class="${lesson.icon || 'bi bi-play-circle-fill'} text-${unit.color} me-2"></i>
                                            <span>${lesson.title}</span>
                                        </div>
                                        <span class="badge bg-light text-dark">${lesson.duration}</span>
                                    </a>
                                `).join('')}
                                <a href="${unit.assessment_link || '#'}" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
                                    <div>
                                        <i class="bi bi-card-checklist text-${unit.color} me-2"></i>
                                        <span>Unit ${index + 1} Assessment</span>
                                    </div>
                                    <span class="badge bg-light text-dark">${unit.assessment_questions}</span>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        // Render practice resources
        const resourcesContainer = document.querySelector('#resources .row');
        if (resourcesContainer) {
            resourcesContainer.innerHTML = subjectData.resources.map(resource => `
                <div class="col-md-4">
                    <div class="card h-100 border-${resource.color} shadow-sm">
                        <div class="card-body text-center p-4">
                            <i class="${resource.icon} display-4 text-${resource.color} mb-3"></i>
                            <h3 class="h4 fw-bold">${resource.title}</h3>
                            <p class="mb-4">${resource.description}</p>
                            <a href="${resource.link || '#'}" class="btn btn-outline-${resource.color}">
                                <i class="${resource.button_icon} me-1"></i>${resource.button_text}
                            </a>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        // Render teacher resources if applicable
        if (typeof userRole !== 'undefined' && userRole === 'teacher' && subjectData.teacher_resources) {
            const teacherResourcesContainer = document.querySelector('#teacher-resources .row');
            if (teacherResourcesContainer) {
                teacherResourcesContainer.innerHTML = subjectData.teacher_resources.map(resource => `
                    <div class="col-md-6">
                        <div class="card h-100 border-${resource.color} shadow-sm">
                            <div class="card-body text-center p-4">
                                <i class="${resource.icon} display-4 text-${resource.color} mb-3"></i>
                                <h3 class="h4 fw-bold">${resource.title}</h3>
                                <p class="mb-4">${resource.description}</p>
                                <a href="${resource.link || '#'}" class="btn btn-outline-${resource.color}">
                                    <i class="${resource.button_icon} me-1"></i>${resource.button_text}
                                </a>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        } else {
            document.getElementById('teacher-resources').style.display = 'none';
        }

        // Update CTA section
        updateElementText('.cta-section h2', subjectData.cta.title);
        updateElementText('.cta-section .lead', subjectData.cta.subtitle);
        const ctaButton = document.querySelector('.cta-section .btn');
        if (ctaButton) {
            ctaButton.innerHTML = `<i class="${subjectData.cta.icon} me-2"></i>${subjectData.cta.button_text}`;
            ctaButton.href = subjectData.cta.link;
        }

        // Initialize Bootstrap components
        if (typeof bootstrap !== 'undefined') {
            const accordionElements = document.querySelectorAll('.accordion-button');
            accordionElements.forEach(el => {
                new bootstrap.Collapse(el, {
                    toggle: false
                });
            });
        }
    }

    // Helper functions
    function updateElementText(selector, text) {
        const element = document.querySelector(selector);
        if (element) element.innerHTML = text;
    }

    function updateElementIcon(selector, iconClass) {
        const element = document.querySelector(selector);
        if (element) {
            element.className = ''; // Clear existing classes
            iconClass.split(' ').forEach(cls => element.classList.add(cls));
        }
    }

    function calculateUserProgress() {
        // In a real app, this would check the user's progress in the database
        // For demo purposes, return a random value or get from localStorage
        return localStorage.getItem(`${grade}_${subject}_progress`) || Math.floor(Math.random() * 100);
    }
});