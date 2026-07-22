class BeforeAfter {
    constructor(enteryObject) {

        const beforeAfterContainer = document.querySelector(enteryObject.id);
        const before = beforeAfterContainer.querySelector('.bal-before');
        const beforeText = beforeAfterContainer.querySelector('.bal-beforePosition');
        const afterText = beforeAfterContainer.querySelector('.bal-afterPosition');
        const handle = beforeAfterContainer.querySelector('.bal-handle');
        var widthChange = 0;

        beforeAfterContainer.querySelector('.bal-before-inset').setAttribute("style", "width: " + beforeAfterContainer.offsetWidth + "px;")
        window.onresize = function () {
            beforeAfterContainer.querySelector('.bal-before-inset').setAttribute("style", "width: " + beforeAfterContainer.offsetWidth + "px;")
        }
        before.setAttribute('style', "width: 50%;");
        handle.setAttribute('style', "left: 50%;");

        //touch screen event listener
        beforeAfterContainer.addEventListener("touchstart", (e) => {

            beforeAfterContainer.addEventListener("touchmove", (e2) => {
                let containerWidth = beforeAfterContainer.offsetWidth;
                let currentPoint = e2.changedTouches[0].clientX;

                let startOfDiv = beforeAfterContainer.offsetLeft;

                let modifiedCurrentPoint = currentPoint - startOfDiv;

                if (modifiedCurrentPoint > 10 && modifiedCurrentPoint < beforeAfterContainer.offsetWidth - 10) {
                    let newWidth = modifiedCurrentPoint * 100 / containerWidth;

                    before.setAttribute('style', "width:" + newWidth + "%;");
                    afterText.setAttribute('style', "z-index: 1;");
                    handle.setAttribute('style', "left:" + newWidth + "%;");
                }
            });
        });

        //mouse move event listener
        beforeAfterContainer.addEventListener('mousemove', (e) => {
            let containerWidth = beforeAfterContainer.offsetWidth;
            widthChange = e.offsetX;
            let newWidth = widthChange * 100 / containerWidth;

            if (e.offsetX > 10 && e.offsetX < beforeAfterContainer.offsetWidth - 10) {
                before.setAttribute('style', "width:" + newWidth + "%;");
                afterText.setAttribute('style', "z-index:" + "1;");
                handle.setAttribute('style', "left:" + newWidth + "%;");
            }
        })

    }
}

document.addEventListener('DOMContentLoaded', () => {
    const VIDEO_LOAD_TIMEOUT_MS = 8000;
    const VIDEO_PRELOAD_ROOT_MARGIN = '900px 0px';
    const INITIAL_VIDEO_LOAD_COUNT = 4;

    const getVideoSource = (video) => {
        const sourceTag = video.querySelector('source');
        return (
            video.getAttribute('src') ||
            video.getAttribute('data-src') ||
            (sourceTag && (sourceTag.getAttribute('src') || sourceTag.getAttribute('data-src'))) ||
            ''
        );
    };

    const attachVideoSource = (video) => {
        const src = getVideoSource(video);
        const sourceTag = video.querySelector('source');

        if (!src) {
            return false;
        }

        if (sourceTag && !sourceTag.getAttribute('src')) {
            sourceTag.setAttribute('src', src);
        } else if (!sourceTag && !video.getAttribute('src')) {
            video.setAttribute('src', src);
        }

        video.dataset.deferredLoaded = 'true';
        return true;
    };

    const getPosterPath = (src) => {
        const normalized = src.replace(/^\.?\//, '');
        return normalized ? `./static/video-posters/${normalized.replace(/\.mp4$/i, '.jpg')}` : '';
    };

    const updateLoadingIndicator = (video, indicator, fallbackText = 'Loading video') => {
        indicator.textContent = fallbackText;
    };

    const syncPosterCropWithVideo = (video, posterFrame) => {
        const videoStyle = window.getComputedStyle(video);
        const objectFit = videoStyle.objectFit || 'cover';
        const objectPosition = videoStyle.objectPosition || '50% 50%';

        posterFrame.style.backgroundSize = objectFit === 'contain' ? 'contain' : 'cover';
        posterFrame.style.backgroundPosition = objectPosition;
    };

    const setupVideoLoadingState = (video) => {
        if (video.parentElement && video.parentElement.classList.contains('video-loading-shell')) {
            return;
        }

        const videoSrc = getVideoSource(video);
        const posterPath = getPosterPath(videoSrc);
        video.setAttribute('preload', 'none');

        const shell = document.createElement('div');
        shell.className = 'video-loading-shell';

        const posterFrame = document.createElement('div');
        posterFrame.className = 'video-poster-frame';
        if (posterPath) {
            posterFrame.style.backgroundImage = `url("${posterPath}")`;
            video.setAttribute('poster', posterPath);
        }

        const indicator = document.createElement('div');
        indicator.className = 'video-loading-indicator';
        indicator.textContent = 'Queued video';
        video._loadingIndicator = indicator;

        const parent = video.parentNode;
        parent.insertBefore(shell, video);
        shell.appendChild(video);
        shell.appendChild(posterFrame);
        shell.appendChild(indicator);
        syncPosterCropWithVideo(video, posterFrame);

        let loadedScheduled = false;
        const markLoaded = () => {
            if (loadedScheduled || shell.classList.contains('is-loaded')) {
                return;
            }
            loadedScheduled = true;
            shell.classList.remove('is-error');
            indicator.textContent = 'Ready';
            window.setTimeout(() => {
                shell.classList.add('is-loaded');
            }, 350);
        };

        const markError = () => {
            shell.classList.remove('is-loaded');
            shell.classList.add('is-error');
            indicator.textContent = 'Video unavailable';
        };

        if (video.readyState >= 2) {
            markLoaded();
        } else {
            video.addEventListener('loadstart', () => {
                updateLoadingIndicator(video, indicator);
            });
            video.addEventListener('loadedmetadata', () => {
                updateLoadingIndicator(video, indicator);
            });
            video.addEventListener('progress', () => {
                updateLoadingIndicator(video, indicator);
            });
            video.addEventListener('timeupdate', () => {
                updateLoadingIndicator(video, indicator);
            });
            video.addEventListener('loadeddata', markLoaded, { once: true });
            video.addEventListener('canplay', markLoaded, { once: true });
            video.addEventListener('playing', markLoaded, { once: true });
            video.addEventListener('error', markError, { once: true });
        }
    };

    const playIfAllowed = (video) => {
        if (!video.autoplay || !video.muted) {
            return;
        }
        if (video.dataset.syncGroup && video.dataset.syncReady !== 'true') {
            return;
        }

        const playAttempt = video.play();
        if (playAttempt && typeof playAttempt.catch === 'function') {
            playAttempt.catch(() => {
                // Mobile browsers may defer autoplay until the user interacts.
            });
        }
    };

    const seekToStart = (video) => {
        try {
            video.currentTime = 0;
        } catch (error) {
            // Some mobile browsers disallow seeking until enough media is buffered.
        }
    };

    const setupDelayedLoopVideos = () => {
        document.querySelectorAll('video[data-loop-delay-ms]').forEach((video) => {
            const delayMs = Number.parseInt(video.dataset.loopDelayMs, 10);
            if (!Number.isFinite(delayMs) || delayMs < 0) {
                return;
            }

            let replayTimer = null;
            video.loop = false;

            const clearReplayTimer = () => {
                if (replayTimer !== null) {
                    window.clearTimeout(replayTimer);
                    replayTimer = null;
                }
            };

            video.addEventListener('ended', () => {
                clearReplayTimer();
                replayTimer = window.setTimeout(() => {
                    seekToStart(video);
                    playIfAllowed(video);
                }, delayMs);
            });

            video.addEventListener('play', clearReplayTimer);
            video.addEventListener('pause', () => {
                if (!video.ended) {
                    clearReplayTimer();
                }
            });
        });
    };

    const loadSingleVideo = (video, options = {}) => new Promise((resolve) => {
        if (video.readyState >= 2 || video.dataset.deferredLoaded === 'true') {
            resolve();
            return;
        }

        let resolved = false;
        const finish = () => {
            if (resolved) {
                return;
            }
            resolved = true;
            clearTimeout(timeoutId);
            video.removeEventListener('loadeddata', finish);
            video.removeEventListener('canplay', finish);
            video.removeEventListener('error', finish);
            resolve();
        };

        const timeoutId = window.setTimeout(finish, VIDEO_LOAD_TIMEOUT_MS);
        video.addEventListener('loadeddata', finish);
        video.addEventListener('canplay', finish);
        video.addEventListener('error', finish);

        if (!attachVideoSource(video)) {
            finish();
            return;
        }

        if (video._loadingIndicator) {
            updateLoadingIndicator(video, video._loadingIndicator);
        }
        video.setAttribute('preload', 'metadata');
        video.load();
        if (!options.deferPlay) {
            playIfAllowed(video);
        }
    });

    const loadVideo = (video, videos, syncGroupLoads) => {
        const syncGroup = video.dataset.syncGroup;
        if (!syncGroup) {
            return loadSingleVideo(video);
        }

        if (syncGroupLoads.has(syncGroup)) {
            return syncGroupLoads.get(syncGroup);
        }

        const groupVideos = videos.filter((candidate) => candidate.dataset.syncGroup === syncGroup);
        const groupLoad = Promise.all(groupVideos.map((groupVideo) => loadSingleVideo(groupVideo, { deferPlay: true })))
            .then(() => {
                groupVideos.forEach((groupVideo) => {
                    groupVideo.dataset.syncReady = 'true';
                });
                groupVideos.forEach(seekToStart);
                window.requestAnimationFrame(() => {
                    groupVideos.forEach(playIfAllowed);
                });
            });

        syncGroupLoads.set(syncGroup, groupLoad);
        return groupLoad;
    };

    const setupViewportPlayback = (videos) => {
        if (!('IntersectionObserver' in window)) {
            videos.forEach(playIfAllowed);
            return;
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                const video = entry.target;
                const groupVideos = video.dataset.syncGroup
                    ? videos.filter((candidate) => candidate.dataset.syncGroup === video.dataset.syncGroup)
                    : [video];

                if (entry.isIntersecting) {
                    groupVideos.forEach(playIfAllowed);
                } else {
                    groupVideos.forEach((groupVideo) => groupVideo.pause());
                }
            });
        }, { rootMargin: '240px 0px', threshold: 0.05 });

        videos.forEach((video) => observer.observe(video));
    };

    const createVideoLoadQueue = (videos) => {
        const pending = new Set(videos);
        const queued = [];
        const syncGroupLoads = new Map();
        const loadCompletions = new Map();
        let nextRequestIndex = 0;
        let active = false;

        const ensureLoadCompletion = (video) => {
            if (!loadCompletions.has(video)) {
                let resolveCompletion;
                const promise = new Promise((resolve) => {
                    resolveCompletion = resolve;
                });
                loadCompletions.set(video, { promise, resolve: resolveCompletion });
            }
            return loadCompletions.get(video).promise;
        };

        const run = async () => {
            if (active) {
                return;
            }
            active = true;
            while (queued.length > 0) {
                const loadUnit = queued.shift();
                await loadVideo(loadUnit.representative, videos, syncGroupLoads);
                loadUnit.videos.forEach((video) => {
                    loadCompletions.get(video).resolve();
                });
            }
            active = false;
        };

        const queueVideo = (video) => {
            if (!pending.has(video)) {
                return;
            }

            const groupVideos = video.dataset.syncGroup
                ? videos.filter((candidate) => candidate.dataset.syncGroup === video.dataset.syncGroup)
                : [video];
            const pendingGroupVideos = groupVideos.filter((groupVideo) => pending.has(groupVideo));
            if (pendingGroupVideos.length === 0) {
                return;
            }

            pendingGroupVideos.forEach((groupVideo) => {
                ensureLoadCompletion(groupVideo);
                pending.delete(groupVideo);
            });
            queued.push({
                representative: video,
                videos: pendingGroupVideos,
            });
        };

        const enqueueThroughIndex = (targetIndex) => {
            if (targetIndex < 0) {
                return;
            }

            const clampedTargetIndex = Math.min(targetIndex, videos.length - 1);
            for (let index = nextRequestIndex; index <= clampedTargetIndex; index += 1) {
                queueVideo(videos[index]);
            }
            nextRequestIndex = Math.max(nextRequestIndex, clampedTargetIndex + 1);
            run();
        };

        return {
            enqueue(video) {
                enqueueThroughIndex(videos.indexOf(video));
                return loadCompletions.has(video)
                    ? loadCompletions.get(video).promise
                    : Promise.resolve();
            },
            enqueueMany(nextVideos) {
                const targetIndexes = nextVideos
                    .map((video) => videos.indexOf(video))
                    .filter((index) => index >= 0);
                if (targetIndexes.length === 0) {
                    return Promise.resolve();
                }
                enqueueThroughIndex(Math.max(...targetIndexes));
                return Promise.all(nextVideos.map((video) => (
                    loadCompletions.has(video) ? loadCompletions.get(video).promise : Promise.resolve()
                )));
            },
            enqueueRemaining() {
                enqueueThroughIndex(videos.length - 1);
                return Promise.all(videos.map((video) => (
                    loadCompletions.has(video) ? loadCompletions.get(video).promise : Promise.resolve()
                )));
            },
        };
    };

    const setupViewportLoading = (videos, loadQueue) => {
        if (!('IntersectionObserver' in window)) {
            loadQueue.enqueueRemaining();
            return;
        }

        const observer = new IntersectionObserver((entries) => {
            const visibleVideos = entries
                .filter((entry) => entry.isIntersecting)
                .map((entry) => entry.target)
                .sort((a, b) => videos.indexOf(a) - videos.indexOf(b));

            loadQueue.enqueueMany(visibleVideos);
            visibleVideos.forEach((video) => observer.unobserve(video));
        }, { rootMargin: VIDEO_PRELOAD_ROOT_MARGIN, threshold: 0.01 });

        videos.forEach((video) => observer.observe(video));
    };

    const scheduleIdleLoading = (loadQueue) => {
        const loadRemaining = () => loadQueue.enqueueRemaining();
        if ('requestIdleCallback' in window) {
            window.requestIdleCallback(loadRemaining, { timeout: 6000 });
        } else {
            window.setTimeout(loadRemaining, 3000);
        }
    };

    const parseStartSeconds = (text) => {
        const match = text.match(/(?:From\s+)?(\d+(?:\.\d+)?)(?:\s*-\s*\d+(?:\.\d+)?)?\s*s/i);
        return match ? Number.parseFloat(match[1]) : 0;
    };

    const waitForSeekableVideo = (video) => new Promise((resolve) => {
        if (video.readyState >= 1) {
            resolve();
            return;
        }

        const finish = () => {
            video.removeEventListener('loadedmetadata', finish);
            video.removeEventListener('canplay', finish);
            video.removeEventListener('error', finish);
            resolve();
        };

        video.addEventListener('loadedmetadata', finish);
        video.addEventListener('canplay', finish);
        video.addEventListener('error', finish);
        attachVideoSource(video);
        video.load();
    });

    const setupCaptionSeekLinks = (loadQueue) => {
        const containerSelector = '.video-tile, .adjustment-card, .failure-card, .elevated-media-card, .synesthetic-prior-card, .teaser-video-section';
        document.querySelectorAll('.video-seek-link').forEach((link) => {
            link.addEventListener('click', async (event) => {
                event.preventDefault();
                const container = link.closest(containerSelector);
                const video = container && container.querySelector('video');
                if (!video) {
                    return;
                }

                await loadQueue.enqueue(video);
                await waitForSeekableVideo(video);
                try {
                    video.currentTime = parseStartSeconds(link.textContent || '');
                } catch (error) {
                    return;
                }
                playIfAllowed(video);
                video.scrollIntoView({ behavior: 'smooth', block: 'center' });
            });
        });
    };

    const setupStickyNavigation = () => {
        const nav = document.querySelector('.sticky-page-nav');
        const navLinks = Array.from(document.querySelectorAll('.sticky-page-nav a[href^="#"]'));
        const sections = navLinks
            .map((link) => ({
                link,
                target: document.querySelector(link.getAttribute('href')),
            }))
            .filter((item) => item.target);

        if (!nav || sections.length === 0) {
            return;
        }

        let currentActiveLink = null;
        let ticking = false;
        let manualNavigationUntil = 0;
        const scrollGapPx = 32;
        const activeLineGapPx = 72;

        const setActiveLink = (nextActiveLink) => {
            if (currentActiveLink === nextActiveLink) {
                return;
            }
            navLinks.forEach((link) => link.classList.toggle('is-active', link === nextActiveLink));
            currentActiveLink = nextActiveLink;
        };

        const updateNavigationState = () => {
            if (performance.now() < manualNavigationUntil) {
                ticking = false;
                return;
            }

            const navHeight = nav.getBoundingClientRect().height;
            const anchorY = window.scrollY + navHeight + activeLineGapPx;
            const activeSection = sections.reduce((current, item) => (
                item.target.getBoundingClientRect().top + window.scrollY <= anchorY ? item : current
            ), null);
            setActiveLink(activeSection ? activeSection.link : null);
            ticking = false;
        };

        const requestNavigationUpdate = () => {
            if (ticking) {
                return;
            }
            ticking = true;
            window.requestAnimationFrame(updateNavigationState);
        };

        updateNavigationState();
        sections.forEach(({ link, target }) => {
            link.addEventListener('click', (event) => {
                event.preventDefault();
                const navHeight = nav.getBoundingClientRect().height;
                const targetY = target.getBoundingClientRect().top + window.scrollY - navHeight - scrollGapPx;

                manualNavigationUntil = performance.now() + 1400;
                setActiveLink(link);
                window.history.pushState(null, '', link.getAttribute('href'));
                window.scrollTo({
                    top: Math.max(0, targetY),
                    behavior: 'smooth',
                });
                window.setTimeout(requestNavigationUpdate, 1450);
            });
        });
        window.addEventListener('scroll', requestNavigationUpdate, { passive: true });
        window.addEventListener('resize', requestNavigationUpdate);
    };

    const videos = Array.from(document.querySelectorAll('video'));
    videos.forEach(setupVideoLoadingState);
    setupDelayedLoopVideos();
    const loadQueue = createVideoLoadQueue(videos);
    loadQueue.enqueueMany(videos.slice(0, INITIAL_VIDEO_LOAD_COUNT));
    setupViewportLoading(videos, loadQueue);
    setupViewportPlayback(videos);
    setupCaptionSeekLinks(loadQueue);
    setupStickyNavigation();
    scheduleIdleLoading(loadQueue);
});