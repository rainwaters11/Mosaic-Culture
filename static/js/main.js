document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    // Handle like button clicks
    document.querySelectorAll('.like-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const storyId = this.dataset.storyId;
            try {
                const response = await fetch(`/like/${storyId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const data = await response.json();
                this.querySelector('.like-count').textContent = data.likes;
                
                // Animate the like button
                this.classList.add('liked');
                setTimeout(() => {
                    this.classList.remove('liked');
                }, 200);
            } catch (error) {
                console.error('Error:', error);
            }
        });
    });

    // File upload preview
    const mediaInput = document.getElementById('media');
    if (mediaInput) {
        mediaInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const fileSize = this.files[0].size / 1024 / 1024; // Convert to MB
                if (fileSize > 16) {
                    alert('File size must be less than 16MB');
                    this.value = '';
                }
            }
        });
    }

    // Form validation
    const storyForm = document.querySelector('form');
    if (storyForm) {
        storyForm.addEventListener('submit', function(e) {
            const title = document.getElementById('title').value.trim();
            const content = document.getElementById('content').value.trim();
            const region = document.getElementById('region').value;

            if (!title || !content || !region) {
                e.preventDefault();
                alert('Please fill in all required fields');
            }
        });
    }
});
