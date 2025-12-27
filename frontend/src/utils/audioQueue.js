/**
 * AudioQueueManager - Manages sequential playback of commentary audio files
 * 
 * Handles queuing of audio events, sequential playback, error handling,
 * and state management for the commentary audio system.
 */
class AudioQueueManager {
    constructor() {
        this.queue = [];
        this.isPlaying = false;
        this.currentAudio = null;
        this.currentEvent = null;
        this.onStateChange = null; // Callback for state updates
    }

    /**
     * Add audio event to queue and start playback if idle
     * @param {Object} audioEvent - Audio event from WebSocket
     * @param {string} audioEvent.audio_url - URL path to audio file
     * @param {string} audioEvent.commentary_text - Commentary text
     * @param {number} audioEvent.move_number - Move number
     * @param {string} audioEvent.latest_move - Latest move notation
     */
    enqueue(audioEvent) {
        this.queue.push(audioEvent);
        
        // Start playback immediately if not currently playing
        if (!this.isPlaying) {
            this.playNext();
        } else {
            // Notify state change for queue length update
            this.notifyStateChange();
        }
    }

    /**
     * Play next audio in queue
     * Automatically continues to next item after current finishes
     */
    async playNext() {
        // Check if queue is empty
        if (this.queue.length === 0) {
            this.isPlaying = false;
            this.currentEvent = null;
            this.notifyStateChange();
            return;
        }

        // Get next event from queue
        const event = this.queue.shift();
        this.isPlaying = true;
        this.currentEvent = event;

        try {
            await this.playAudio(event);
        } catch (error) {
            console.error('Audio playback failed:', error, event);
            // Continue to next audio even if current fails
        }

        // Play next audio after current finishes (or fails)
        this.playNext();
    }

    /**
     * Play a single audio file
     * @param {Object} event - Audio event to play
     * @returns {Promise} Resolves when audio finishes, rejects on error
     */
    async playAudio(event) {
        return new Promise((resolve, reject) => {
            // Construct full audio URL
            const audioUrl = `http://127.0.0.1:8000${event.audio_url}`;
            const audio = new Audio(audioUrl);
            this.currentAudio = audio;

            // Handle successful playback completion
            audio.onended = () => {
                this.currentAudio = null;
                resolve();
            };

            // Handle audio loading errors
            audio.onerror = (error) => {
                this.currentAudio = null;
                reject(new Error(`Audio load failed: ${audioUrl}`));
            };

            // Notify state change with current event
            this.notifyStateChange(event);

            // Start playback
            audio.play().catch((playError) => {
                this.currentAudio = null;
                reject(new Error(`Audio play failed: ${playError.message}`));
            });
        });
    }

    /**
     * Clear all queued audio and stop current playback
     */
    clear() {
        // Clear the queue
        this.queue = [];

        // Stop current audio if playing
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
        }

        this.isPlaying = false;
        this.currentEvent = null;
        this.notifyStateChange();
    }

    /**
     * Notify state change callback with current state
     * @param {Object|null} currentEvent - Current audio event being played
     */
    notifyStateChange(currentEvent = null) {
        if (this.onStateChange) {
            this.onStateChange({
                isPlaying: this.isPlaying,
                queueLength: this.queue.length,
                currentEvent: currentEvent || this.currentEvent
            });
        }
    }

    /**
     * Get current queue length
     * @returns {number} Number of items in queue
     */
    getQueueLength() {
        return this.queue.length;
    }

    /**
     * Check if audio is currently playing
     * @returns {boolean} True if audio is playing
     */
    getIsPlaying() {
        return this.isPlaying;
    }

    /**
     * Get current event being played
     * @returns {Object|null} Current audio event or null
     */
    getCurrentEvent() {
        return this.currentEvent;
    }
}

export default AudioQueueManager;
