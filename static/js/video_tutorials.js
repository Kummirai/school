// Video Tutorials Page Script
document.addEventListener('DOMContentLoaded', function() {
    let allVideos = [];
    let currentFilters = {
        grade: '',
        subject: '',
        searchTerm: ''
    };
    
    // Initialize UI components
    initializeUI();
    
    function initializeUI() {
        // Setup filter and search functionality
        setupFiltersAndSearch();
    }
    
    function toggleLoadingSpinner(show) {
        const spinner = document.getElementById('loading-spinner');
        if (show) {
            spinner.classList.remove('d-none');
        } else {
            spinner.classList.add('d-none');
        }
    }
    
    function showErrorMessage(message) {
        const videosContainer = document.getElementById('videos-container');
        videosContainer.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger">${message}</div>
            </div>
        `;
    }
    
    function displayVideos(videos) {
        const container = document.getElementById('videos-container');
        container.innerHTML = '';
        
        if (videos.length === 0) {
            document.getElementById('no-results').classList.remove('d-none');
            return;
        }
        
        document.getElementById('no-results').classList.add('d-none');
        
        const fragment = document.createDocumentFragment();
        
        videos.forEach(video => {
            const videoCol = document.createElement('div');
            videoCol.className = 'col-md-4 col-lg-3 mb-4';
            
            videoCol.innerHTML = `
                <div class="card video-card h-100">
                    <img data-src="${video.thumbnail}" class="card-img-top lazy loading" alt="${video.title}" style="height: 180px; object-fit: cover;">
                    <div class="card-body">
                        <h5 class="card-title" style="font-size: 1rem;">${video.title}</h5>
                        <p class="card-text" style="font-size: 0.9rem;">${video.description}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="badge bg-primary subject-badge" style="font-size: 0.75rem">${video.subject}</span>
                            <span class="badge bg-secondary subject-badge" style="font-size: 0.75rem">${video.grade}</span>
                        </div>
                    </div>
                    <div class="card-footer bg-transparent">
                        <button class="btn btn-sm btn-primary watch-btn w-100" data-video-id="${video.youtubeId}">
                            <i class="bi bi-play-fill"></i> Watch Now
                        </button>
                    </div>
                </div>
            `;
            
            fragment.appendChild(videoCol);
        });
        
        container.appendChild(fragment);
        
        // Add event listeners to watch buttons
        setupWatchButtons();
        
        // Initialize lazy loading
        initLazyLoading();
    }
    
    function initLazyLoading() {
        const lazyImages = document.querySelectorAll('img.lazy');
        
        if ('IntersectionObserver' in window) {
            const lazyImageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const lazyImage = entry.target;
                        lazyImage.src = lazyImage.dataset.src;
                        lazyImage.classList.remove('lazy', 'loading');
                        lazyImageObserver.unobserve(lazyImage);
                    }
                });
            }, {
                rootMargin: '100px 0px'
            });

            lazyImages.forEach(lazyImage => {
                lazyImageObserver.observe(lazyImage);
            });
        } else {
            // Fallback for older browsers
            lazyImages.forEach(lazyImage => {
                lazyImage.src = lazyImage.dataset.src;
                lazyImage.classList.remove('lazy', 'loading');
            });
        }
    }
    
    function setupWatchButtons() {
        document.querySelectorAll('.watch-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const videoId = this.getAttribute('data-video-id');
                openVideoModal(videoId);
            });
        });
    }
    
    function populateSubjectDropdown(videos) {
        const subjectSelect = document.getElementById('subject-select');
        
        // Get unique subjects from videos filtered by selected grade
        const selectedGrade = document.getElementById('grade-select').value;
        const filteredVideos = videos.filter(video => {
            if (video.grade.includes('-')) {
                const gradeRange = video.grade.replace('Grade ', '').split('-');
                const startGrade = parseInt(gradeRange[0]);
                const endGrade = parseInt(gradeRange[1]);
                return parseInt(selectedGrade) >= startGrade && parseInt(selectedGrade) <= endGrade;
            } else {
                return video.grade === `Grade ${selectedGrade}`;
            }
        });
        
        const subjects = [...new Set(filteredVideos.map(video => video.subject))];
        
        // Clear existing options except the first one
        while (subjectSelect.options.length > 1) {
            subjectSelect.remove(1);
        }
        
        // Add subjects to dropdown
        subjects.sort().forEach(subject => {
            const option = document.createElement('option');
            option.value = subject;
            option.textContent = subject;
            subjectSelect.appendChild(option);
        });
    }
    
    function setupFiltersAndSearch() {
        const gradeSelect = document.getElementById('grade-select');
        const subjectSelect = document.getElementById('subject-select');
        const applyFiltersBtn = document.getElementById('apply-filters');
        const searchInput = document.getElementById('video-search');
        const searchBtn = document.getElementById('search-btn');
        
        // Update subjects when grade changes
        gradeSelect.addEventListener('change', async function() {
            if (!this.value) return;
            
            try {
                toggleLoadingSpinner(true);
                
                // Load videos if not already loaded
                if (allVideos.length === 0) {
                    const response = await fetch('static/js/video_tutorials.json');
                    if (!response.ok) {
                        throw new Error('Failed to load videos');
                    }
                    const data = await response.json();
                    allVideos = data.videos;
                }
                
                populateSubjectDropdown(allVideos);
                toggleLoadingSpinner(false);
            } catch (error) {
                console.error('Error loading videos:', error);
                showErrorMessage('Failed to load videos. Please try again later.');
            }
        });
        
        // Apply filters when button is clicked
        applyFiltersBtn.addEventListener('click', applyFilters);
        
        // Apply filters when Enter is pressed in search
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applyFilters();
            }
        });
        
        // Apply filters when search button is clicked
        searchBtn.addEventListener('click', applyFilters);
        
        async function applyFilters() {
            if (!gradeSelect.value || !subjectSelect.value) {
                alert('Please select both grade and subject');
                return;
            }
            
            try {
                toggleLoadingSpinner(true);
                
                // Load videos if not already loaded
                if (allVideos.length === 0) {
                    const response = await fetch('scripts/video_tutorials.json');
                    if (!response.ok) {
                        throw new Error('Failed to load videos');
                    }
                    const data = await response.json();
                    allVideos = data.videos;
                }
                
                currentFilters.grade = gradeSelect.value;
                currentFilters.subject = subjectSelect.value;
                currentFilters.searchTerm = searchInput.value.toLowerCase();
                
                const filteredVideos = filterVideos(allVideos, currentFilters);
                displayVideos(filteredVideos);
                
                toggleLoadingSpinner(false);
            } catch (error) {
                console.error('Error loading videos:', error);
                showErrorMessage('Failed to load videos. Please try again later.');
            }
        }
    }
    
    function filterVideos(videos, filters) {
        let filteredVideos = [...videos];
        
        // Filter by grade
        filteredVideos = filteredVideos.filter(video => {
            if (video.grade.includes('-')) {
                const gradeRange = video.grade.replace('Grade ', '').split('-');
                const startGrade = parseInt(gradeRange[0]);
                const endGrade = parseInt(gradeRange[1]);
                return parseInt(filters.grade) >= startGrade && parseInt(filters.grade) <= endGrade;
            } else {
                return video.grade === `Grade ${filters.grade}`;
            }
        });
        
        // Filter by subject
        filteredVideos = filteredVideos.filter(video => video.subject === filters.subject);
        
        // Apply search term if exists
        if (filters.searchTerm) {
            filteredVideos = filteredVideos.filter(video => 
                video.title.toLowerCase().includes(filters.searchTerm) || 
                video.description.toLowerCase().includes(filters.searchTerm) ||
                video.subject.toLowerCase().includes(filters.searchTerm) ||
                video.grade.toLowerCase().includes(filters.searchTerm)
            );
        }
        
        return filteredVideos;
    }
    
    function openVideoModal(videoId) {
        // Create modal structure
        const modalHTML = `
        <div class="modal fade" id="videoModal" tabindex="-1" aria-hidden="true" style="display: none;">
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Video Tutorial</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body p-0">
                        <div class="video-container">
                            <iframe src="https://www.youtube.com/embed/${videoId}?autoplay=1" 
                                    frameborder="0" 
                                    allowfullscreen
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                            </iframe>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `;
    
        // Remove any existing modal first
        const existingModal = document.getElementById('videoModal');
        if (existingModal) existingModal.remove();
    
        // Add new modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    
        // Initialize and show modal
        const videoModal = new bootstrap.Modal(document.getElementById('videoModal'));
        videoModal.show();
    
        // Clean up when modal closes
        document.getElementById('videoModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    }
});