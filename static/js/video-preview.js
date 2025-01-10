/**
 * Video Preview Animation Module
 */
class VideoPreviewManager {
    constructor(previewContainerId) {
        this.container = document.getElementById(previewContainerId);
        this.previewId = null;
        this.progressInterval = null;
        this.isGenerating = false;
    }

    initialize() {
        // Create preview elements
        this.container.innerHTML = `
            <div class="video-preview-container">
                <div class="progress-ring">
                    <svg class="progress-ring__circle" width="120" height="120">
                        <circle class="progress-ring__circle-bg" r="52" cx="60" cy="60" />
                        <circle class="progress-ring__circle-progress" r="52" cx="60" cy="60" />
                    </svg>
                    <div class="progress-text">0%</div>
                </div>
                <div class="status-message">Initializing...</div>
                <div class="preview-result" style="display: none;">
                    <video controls style="max-width: 100%; display: none;"></video>
                </div>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .video-preview-container {
                text-align: center;
                padding: 20px;
            }

            .progress-ring {
                position: relative;
                display: inline-block;
            }

            .progress-ring__circle {
                transform: rotate(-90deg);
            }

            .progress-ring__circle-bg,
            .progress-ring__circle-progress {
                fill: none;
                stroke-width: 8;
            }

            .progress-ring__circle-bg {
                stroke: #ddd;
            }

            .progress-ring__circle-progress {
                stroke: var(--accent-color);
                stroke-dasharray: 326.726;
                stroke-dashoffset: 326.726;
                transition: stroke-dashoffset 0.3s ease;
            }

            .progress-text {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 1.2rem;
                font-weight: bold;
            }

            .status-message {
                margin-top: 1rem;
                font-size: 1rem;
                color: var(--text-color);
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }

            .generating .progress-ring {
                animation: pulse 2s infinite;
            }
        `;
        document.head.appendChild(style);
    }

    startPreview(previewId) {
        this.previewId = previewId;
        this.isGenerating = true;
        this.container.querySelector('.video-preview-container').classList.add('generating');
        this.startProgressCheck();
    }

    updateProgress(progress, message) {
        const circle = this.container.querySelector('.progress-ring__circle-progress');
        const text = this.container.querySelector('.progress-text');
        const status = this.container.querySelector('.status-message');
        
        const circumference = 2 * Math.PI * 52;
        const offset = circumference - (progress / 100) * circumference;
        
        circle.style.strokeDashoffset = offset;
        text.textContent = `${Math.round(progress)}%`;
        status.textContent = message;
    }

    async checkProgress() {
        try {
            const response = await fetch(`/api/video-preview/${this.previewId}`);
            const data = await response.json();

            this.updateProgress(data.progress, data.message);

            if (data.status === 'completed') {
                this.showVideo(data.video_url);
                this.stopPreview();
            } else if (data.status === 'error') {
                this.showError(data.message);
                this.stopPreview();
            }
        } catch (error) {
            console.error('Error checking preview status:', error);
        }
    }

    startProgressCheck() {
        this.progressInterval = setInterval(() => this.checkProgress(), 1000);
    }

    stopPreview() {
        this.isGenerating = false;
        clearInterval(this.progressInterval);
        this.container.querySelector('.video-preview-container').classList.remove('generating');
    }

    showVideo(videoUrl) {
        const videoElement = this.container.querySelector('video');
        const previewResult = this.container.querySelector('.preview-result');
        
        videoElement.src = videoUrl;
        videoElement.style.display = 'block';
        previewResult.style.display = 'block';
    }

    showError(message) {
        const status = this.container.querySelector('.status-message');
        status.textContent = `Error: ${message}`;
        status.style.color = 'var(--red-color)';
    }
}

// Export the manager
window.VideoPreviewManager = VideoPreviewManager;
