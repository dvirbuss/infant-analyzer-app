const uploadedFiles = {
    prone: null,
    supine: null
};

// Set default date to today minus 60 days
document.addEventListener("DOMContentLoaded", () => {
    const defaultDate = new Date();
    defaultDate.setDate(defaultDate.getDate() - 60);
    document.getElementById("birth-date").value = defaultDate.toISOString().split('T')[0];
});

function handleFileSelect(event, pose) {
    const file = event.target.files[0];
    if (!file) return;

    uploadedFiles[pose] = file;
    
    // UI Updates
    document.getElementById(`card-${pose}`).querySelector('.upload-area').style.display = 'none';
    const previewArea = document.getElementById(`preview-${pose}`);
    previewArea.style.display = 'block';
    
    const videoObj = document.getElementById(`vid-${pose}`);
    const fileURL = URL.createObjectURL(file);
    videoObj.src = fileURL;

    checkGenerateButton();
}

function clearFile(pose) {
    uploadedFiles[pose] = null;
    document.getElementById(`file-${pose}`).value = "";
    
    // UI Updates
    document.getElementById(`card-${pose}`).querySelector('.upload-area').style.display = 'block';
    
    const previewArea = document.getElementById(`preview-${pose}`);
    previewArea.style.display = 'none';
    const videoObj = document.getElementById(`vid-${pose}`);
    videoObj.pause();
    videoObj.removeAttribute('src');
    videoObj.load();

    checkGenerateButton();
}

function checkGenerateButton() {
    // Enable button if AT LEAST ONE required file is present
    const isReady = uploadedFiles.prone || uploadedFiles.supine;
    document.getElementById('generate-btn').disabled = !isReady;
}

let progressInterval = null;

async function pollProgress() {
    try {
        const res = await fetch('/progress');
        const data = await res.json();
        if (data.status === 'processing' && data.pose !== 'None') {
            const percent = Math.min((data.frame / data.total_frames) * 100, 100);
            
            const poses = ['Prone', 'Supine'];
            const activeIndex = data.pose_index - 1; // 0 or 1
            
            // Update the active one
            if (activeIndex >= 0 && activeIndex < 3) {
                const p = poses[activeIndex];
                document.getElementById(`step-${p}`).className = 'progress-step';
                
                const degrees = Math.round(percent * 3.6);
                document.getElementById(`circle-${p}`).style.background = `conic-gradient(var(--primary-color) ${degrees}deg, #E2E8F0 0deg)`;
                document.getElementById(`val-${p}`).innerText = `${Math.round(percent)}%`;
                document.getElementById(`linear-${p}`).style.width = `${percent}%`;
                
                // Mark previous as completed
                for (let i = 0; i < activeIndex; i++) {
                    document.getElementById(`step-${poses[i]}`).className = 'progress-step completed';
                    document.getElementById(`val-${poses[i]}`).innerText = '100%';
                }
            }
        }
    } catch(e) {
        console.error("Polling error", e);
    }
}

async function generateReport() {
    const dateVal = document.getElementById("birth-date").value;
    if (!dateVal) {
        alert("Please select Infant Birthday");
        return;
    }

    const formData = new FormData();
    formData.append("birth_date", dateVal);
    if (uploadedFiles.prone) {
        formData.append("prone", uploadedFiles.prone);
    }
    if (uploadedFiles.supine) {
        formData.append("supine", uploadedFiles.supine);
    }

    // Show Loading
    document.getElementById('loading-overlay').style.display = 'flex';
    document.getElementById('results-section').style.display = 'none';

    // Reset and configure Progress UI based on which videos are present
    const stepProne = document.getElementById('step-Prone');
    const stepSupine = document.getElementById('step-Supine');
    const progArrow = document.getElementById('prog-arrow');

    // Reset styles
    ['Prone', 'Supine'].forEach(pose => {
        document.getElementById(`step-${pose}`).className = 'progress-step inactive';
        document.getElementById(`circle-${pose}`).style.background = `conic-gradient(var(--primary-color) 0deg, #E2E8F0 0deg)`;
        document.getElementById(`val-${pose}`).innerText = '0%';
        document.getElementById(`linear-${pose}`).style.width = '0%';
    });

    if (uploadedFiles.prone && uploadedFiles.supine) {
        stepProne.style.display = 'flex';
        stepSupine.style.display = 'flex';
        progArrow.style.display = 'block';
        
        stepProne.querySelector('.step-label').innerText = 'Prone 1/2';
        stepSupine.querySelector('.step-label').innerText = 'Supine 2/2';
        stepProne.className = 'progress-step'; // First active
    } else if (uploadedFiles.prone) {
        stepProne.style.display = 'flex';
        stepSupine.style.display = 'none';
        progArrow.style.display = 'none';
        
        stepProne.querySelector('.step-label').innerText = 'Prone';
        stepProne.className = 'progress-step'; // Active
    } else if (uploadedFiles.supine) {
        stepProne.style.display = 'none';
        stepSupine.style.display = 'flex';
        progArrow.style.display = 'none';
        
        stepSupine.querySelector('.step-label').innerText = 'Supine';
        stepSupine.className = 'progress-step'; // Active
    }
    
    // Start Polling
    progressInterval = setInterval(pollProgress, 300);

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errBody = await response.text();
            throw new Error(errBody || response.statusText);
        }

        const data = await response.json();
        
        // Hide Loader
        document.getElementById('loading-overlay').style.display = 'none';
        
        // Populate and Show Results
        document.getElementById('results-section').style.display = 'block';
        document.getElementById('aims-score-text').innerText = data.aims_score;
        
        if (data.reports.expert_plot_url) {
            document.getElementById('expert-img').src = data.reports.expert_plot_url;
        }
        if (data.reports.parent_plot_url) {
            document.getElementById('parent-img').src = data.reports.parent_plot_url;
        }
        if (data.reports.supine_table_url) {
            document.getElementById('supine-table-img').src = data.reports.supine_table_url;
            document.getElementById('supine-table-card').style.display = 'block';
        } else {
            document.getElementById('supine-table-card').style.display = 'none';
        }
        
        // Scroll to results
        document.getElementById('results-section').scrollIntoView({behavior: 'smooth'});
        
    } catch (err) {
        document.getElementById('loading-overlay').style.display = 'none';
        alert("Error during analysis: " + err.message);
    } finally {
        if (progressInterval) {
            clearInterval(progressInterval);
        }
        
        // Mark all as completed visually just in case
        if (document.getElementById('loading-overlay').style.display === 'none') {
            ['Prone', 'Supine'].forEach(pose => {
                document.getElementById(`step-${pose}`).className = 'progress-step completed';
            });
        }
    }
}
