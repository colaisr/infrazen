/**
 * Business Context - Visual Resource Mapping
 * 
 * This module handles the visual board interface for mapping cloud resources
 * to business contexts (customers, features, departments, etc.)
 */

// Global state
let currentBoard = null;
let fabricCanvas = null;
let allResources = [];
let currentFilter = 'all';
let autoSaveTimer = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeBusinessContext();
});

/**
 * Main initialization function
 */
function initializeBusinessContext() {
    setupEventListeners();
    
    // Check if we should restore a previously opened board
    const lastBoardId = localStorage.getItem('business_context_last_board');
    
    if (lastBoardId && lastBoardId !== 'list') {
        // Try to open the last board
        openBoard(parseInt(lastBoardId));
    } else {
        // Show board list
        loadBoards();
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Create board button (in header)
    const createBoardBtnHeader = document.getElementById('createBoardBtnHeader');
    if (createBoardBtnHeader) {
        createBoardBtnHeader.addEventListener('click', openCreateBoardModal);
    }
    
    // Keep backward compatibility with old button ID
    const createBoardBtn = document.getElementById('createBoardBtn');
    if (createBoardBtn) {
        createBoardBtn.addEventListener('click', openCreateBoardModal);
    }
    
    // Back to list button
    const backToListBtn = document.getElementById('backToListBtn');
    if (backToListBtn) {
        backToListBtn.addEventListener('click', backToList);
    }
    
    // Zoom controls
    document.getElementById('zoomInBtn')?.addEventListener('click', zoomIn);
    document.getElementById('zoomOutBtn')?.addEventListener('click', zoomOut);
    document.getElementById('zoomResetBtn')?.addEventListener('click', zoomReset);
    
    // Toolbox toggle
    document.getElementById('toggleToolboxBtn')?.addEventListener('click', toggleToolbox);
    document.getElementById('closeToolboxBtn')?.addEventListener('click', toggleToolbox);
    
    // Save board button
    document.getElementById('saveBoardBtn')?.addEventListener('click', saveBoard);
    
    // Board name editing
    const boardNameEl = document.getElementById('currentBoardName');
    if (boardNameEl) {
        boardNameEl.addEventListener('blur', function() {
            if (currentBoard && boardNameEl.textContent.trim() !== currentBoard.name) {
                updateBoardName(boardNameEl.textContent.trim());
            }
        });
        
        boardNameEl.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                boardNameEl.blur();
            }
        });
    }
    
    // Toolbox section toggle
    document.querySelectorAll('.toolbox-section-header').forEach(header => {
        header.addEventListener('click', function() {
            const section = this.closest('.toolbox-section');
            section.classList.toggle('expanded');
        });
    });
    
    // Resource filters
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentFilter = this.dataset.filter;
            filterResources();
        });
    });
    
    // Resource search
    const searchInput = document.getElementById('resourceSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterResources();
        });
    }
    
    // Setup group tool drag
    setupGroupTool();
    
    // Setup free objects tools
    setupFreeObjectsTools();
    
    // Setup properties panel
    setupPropertiesPanel();
    
    // Setup keyboard shortcuts
    setupKeyboardShortcuts();
}

/**
 * Setup group tool drag functionality
 */
function setupGroupTool() {
    const groupTool = document.querySelector('[data-tool="group"]');
    if (!groupTool) return;
    
    groupTool.addEventListener('click', function() {
        createGroupOnCanvas();
    });
}

/**
 * Setup free objects tools (text, rectangle)
 */
function setupFreeObjectsTools() {
    // Text tool
    const textTool = document.querySelector('[data-tool="text"]');
    if (textTool) {
        textTool.addEventListener('click', function() {
            createTextOnCanvas();
        });
    }
    
    // Rectangle tool
    const rectangleTool = document.querySelector('[data-tool="rectangle"]');
    if (rectangleTool) {
        rectangleTool.addEventListener('click', function() {
            createRectangleOnCanvas();
        });
    }
}

/**
 * Setup properties panel
 */
function setupPropertiesPanel() {
    const propertiesPanel = document.getElementById('propertiesPanel');
    const closePropertiesBtn = document.getElementById('closePropertiesBtn');
    
    // Close properties panel
    if (closePropertiesBtn) {
        closePropertiesBtn.addEventListener('click', function() {
            propertiesPanel.style.display = 'none';
        });
    }
    
    // Text properties
    document.getElementById('fontSize')?.addEventListener('change', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.objectType === 'freeText') {
            activeObj.set('fontSize', parseInt(this.value));
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    document.getElementById('boldBtn')?.addEventListener('click', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.objectType === 'freeText') {
            const isBold = activeObj.fontWeight === 'bold';
            activeObj.set('fontWeight', isBold ? 'normal' : 'bold');
            this.classList.toggle('active', !isBold);
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    document.getElementById('italicBtn')?.addEventListener('click', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.objectType === 'freeText') {
            const isItalic = activeObj.fontStyle === 'italic';
            activeObj.set('fontStyle', isItalic ? 'normal' : 'italic');
            this.classList.toggle('active', !isItalic);
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    document.getElementById('underlineBtn')?.addEventListener('click', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.objectType === 'freeText') {
            activeObj.set('underline', !activeObj.underline);
            this.classList.toggle('active', activeObj.underline);
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    document.getElementById('textColor')?.addEventListener('input', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.objectType === 'freeText') {
            activeObj.set('fill', this.value);
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    // Rectangle properties
    document.getElementById('rectFillColor')?.addEventListener('input', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.objectType === 'freeRect') {
            const opacity = document.getElementById('rectOpacity').value / 100;
            activeObj.set('fill', hexToRgba(this.value, opacity));
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    document.getElementById('rectOpacity')?.addEventListener('input', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.objectType === 'freeRect') {
            const color = document.getElementById('rectFillColor').value;
            const opacity = this.value / 100;
            activeObj.set('fill', hexToRgba(color, opacity));
            document.getElementById('rectOpacityValue').textContent = this.value + '%';
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    document.getElementById('rectStrokeColor')?.addEventListener('input', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && activeObj.objectType === 'freeRect') {
            activeObj.set('stroke', this.value);
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    // Layer ordering
    document.getElementById('bringToFrontBtn')?.addEventListener('click', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj) {
            fabricCanvas.bringToFront(activeObj);
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    document.getElementById('sendToBackBtn')?.addEventListener('click', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj) {
            fabricCanvas.sendToBack(activeObj);
            fabricCanvas.renderAll();
            scheduleAutoSave();
        }
    });
    
    // Delete object
    document.getElementById('deleteObjectBtn')?.addEventListener('click', function() {
        const activeObj = fabricCanvas.getActiveObject();
        if (activeObj && (activeObj.objectType === 'freeText' || activeObj.objectType === 'freeRect')) {
            fabricCanvas.remove(activeObj);
            fabricCanvas.renderAll();
            hidePropertiesPanel();
            scheduleAutoSave();
        }
    });
}

/**
 * Show properties panel for selected object
 */
function showPropertiesPanel(obj) {
    if (!obj || (obj.objectType !== 'freeText' && obj.objectType !== 'freeRect')) {
        hidePropertiesPanel();
        return;
    }
    
    const propertiesPanel = document.getElementById('propertiesPanel');
    const textProperties = document.getElementById('textProperties');
    const rectangleProperties = document.getElementById('rectangleProperties');
    
    // Hide all property sections
    textProperties.style.display = 'none';
    rectangleProperties.style.display = 'none';
    
    // Show relevant properties
    if (obj.objectType === 'freeText') {
        textProperties.style.display = 'block';
        
        // Update controls to match object
        document.getElementById('fontSize').value = obj.fontSize || 24;
        document.getElementById('textColor').value = obj.fill || '#1F2937';
        document.getElementById('boldBtn').classList.toggle('active', obj.fontWeight === 'bold');
        document.getElementById('italicBtn').classList.toggle('active', obj.fontStyle === 'italic');
        document.getElementById('underlineBtn').classList.toggle('active', obj.underline === true);
    } else if (obj.objectType === 'freeRect') {
        rectangleProperties.style.display = 'block';
        
        // Extract color from rgba
        const fillColor = obj.fill || 'rgba(59, 130, 246, 0.2)';
        const rgb = fillColor.match(/\d+/g);
        if (rgb) {
            const hex = '#' + [rgb[0], rgb[1], rgb[2]].map(x => parseInt(x).toString(16).padStart(2, '0')).join('');
            document.getElementById('rectFillColor').value = hex;
            const opacity = rgb[3] ? Math.round(parseFloat(rgb[3]) * 100) : 20;
            document.getElementById('rectOpacity').value = opacity;
            document.getElementById('rectOpacityValue').textContent = opacity + '%';
        }
        document.getElementById('rectStrokeColor').value = obj.stroke || '#3B82F6';
    }
    
    propertiesPanel.style.display = 'flex';
}

/**
 * Hide properties panel
 */
function hidePropertiesPanel() {
    document.getElementById('propertiesPanel').style.display = 'none';
}

/**
 * Setup keyboard shortcuts (copy, paste, delete, etc.)
 */
function setupKeyboardShortcuts() {
    let copiedObject = null;
    
    document.addEventListener('keydown', function(e) {
        // Don't trigger shortcuts when typing in text
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // Copy: Ctrl+C or Cmd+C
        if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
            const activeObj = fabricCanvas?.getActiveObject();
            if (activeObj && (activeObj.objectType === 'freeText' || activeObj.objectType === 'freeRect')) {
                e.preventDefault();
                copiedObject = activeObj;
            }
        }
        
        // Paste: Ctrl+V or Cmd+V
        if ((e.ctrlKey || e.metaKey) && e.key === 'v') {
            if (copiedObject) {
                e.preventDefault();
                pasteObject(copiedObject);
            }
        }
        
        // Delete: Delete or Backspace
        if (e.key === 'Delete' || e.key === 'Backspace') {
            const activeObj = fabricCanvas?.getActiveObject();
            if (activeObj && (activeObj.objectType === 'freeText' || activeObj.objectType === 'freeRect')) {
                // Don't delete if we're editing text
                if (activeObj.objectType === 'freeText' && activeObj.isEditing) {
                    return;
                }
                e.preventDefault();
                fabricCanvas.remove(activeObj);
                fabricCanvas.renderAll();
                hidePropertiesPanel();
                scheduleAutoSave();
            }
        }
        
        // Bring to front: Ctrl+]
        if ((e.ctrlKey || e.metaKey) && e.key === ']') {
            const activeObj = fabricCanvas?.getActiveObject();
            if (activeObj) {
                e.preventDefault();
                fabricCanvas.bringToFront(activeObj);
                fabricCanvas.renderAll();
                scheduleAutoSave();
            }
        }
        
        // Send to back: Ctrl+[
        if ((e.ctrlKey || e.metaKey) && e.key === '[') {
            const activeObj = fabricCanvas?.getActiveObject();
            if (activeObj) {
                e.preventDefault();
                fabricCanvas.sendToBack(activeObj);
                fabricCanvas.renderAll();
                scheduleAutoSave();
            }
        }
    });
}

/**
 * Paste (duplicate) an object
 */
function pasteObject(obj) {
    if (!fabricCanvas || !obj) return;
    
    obj.clone(function(cloned) {
        cloned.set({
            left: cloned.left + 20,
            top: cloned.top + 20
        });
        fabricCanvas.add(cloned);
        fabricCanvas.setActiveObject(cloned);
        fabricCanvas.renderAll();
        scheduleAutoSave();
    });
}

/**
 * Load boards list from API
 */
async function loadBoards() {
    const boardsGrid = document.getElementById('boardsGrid');
    const emptyState = document.getElementById('emptyState');
    
    try {
        const response = await fetch('/api/business-context/boards');
        const data = await response.json();
        
        if (data.success) {
            displayBoards(data.boards);
        } else {
            // Check for authentication error
            if (response.status === 401 || data.redirect) {
                window.location.href = data.redirect || '/api/auth/login';
                return;
            }
            
            // Show empty state on other errors
            boardsGrid.style.display = 'none';
            emptyState.style.display = 'block';
            showFlashMessage('error', data.error || 'Failed to load boards');
        }
    } catch (error) {
        console.error('Error loading boards:', error);
        boardsGrid.style.display = 'none';
        emptyState.style.display = 'block';
        showFlashMessage('error', 'Failed to load boards. Please refresh the page.');
    }
}

/**
 * Display boards in grid
 */
function displayBoards(boards) {
    const boardsGrid = document.getElementById('boardsGrid');
    const emptyState = document.getElementById('emptyState');
    
    if (!boards || boards.length === 0) {
        boardsGrid.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    boardsGrid.style.display = 'grid';
    emptyState.style.display = 'none';
    
    boardsGrid.innerHTML = boards.map(board => `
        <div class="board-card" onclick="openBoard(${board.id})">
            <div class="board-card-header">
                <h3 class="board-card-title">${escapeHtml(board.name)}</h3>
                ${board.is_default ? '<span class="board-card-badge">По умолчанию</span>' : ''}
            </div>
            <div class="board-card-meta">
                <div class="board-card-meta-item">
                    <i class="fa-solid fa-cube"></i>
                    <span>${board.resource_count} ресурсов</span>
                </div>
                <div class="board-card-meta-item">
                    <i class="fa-solid fa-object-group"></i>
                    <span>${board.group_count} групп</span>
                </div>
            </div>
            <div class="board-card-actions" onclick="event.stopPropagation()">
                <button class="board-card-btn btn-delete" onclick="deleteBoard(${board.id})">
                    <i class="fa-solid fa-trash"></i>
                    Удалить
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Open create board modal
 */
function openCreateBoardModal() {
    const modal = document.getElementById('createBoardModal');
    modal.classList.add('active');
    document.getElementById('boardName').focus();
}

/**
 * Close create board modal
 */
function closeCreateBoardModal() {
    const modal = document.getElementById('createBoardModal');
    modal.classList.remove('active');
    document.getElementById('boardName').value = '';
}

/**
 * Create new board
 */
async function createBoard() {
    const nameInput = document.getElementById('boardName');
    const name = nameInput.value.trim();
    
    if (!name) {
        showFlashMessage('error', 'Please enter a board name');
        return;
    }
    
    try {
        const response = await fetch('/api/business-context/boards', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        
        const data = await response.json();
        
        if (data.success) {
            closeCreateBoardModal();
            openBoard(data.board.id);
        } else {
            showFlashMessage('error', data.error || 'Failed to create board');
        }
    } catch (error) {
        console.error('Error creating board:', error);
        showFlashMessage('error', 'Failed to create board');
    }
}

/**
 * Delete board
 */
async function deleteBoard(boardId) {
    if (!confirm('Вы уверены, что хотите удалить эту доску? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/business-context/boards/${boardId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // If we deleted the currently viewed board, clear the saved state
            const lastBoardId = localStorage.getItem('business_context_last_board');
            if (lastBoardId == boardId) {
                localStorage.setItem('business_context_last_board', 'list');
            }
            
            loadBoards();
        } else {
            showFlashMessage('error', data.error || 'Failed to delete board');
        }
    } catch (error) {
        console.error('Error deleting board:', error);
        showFlashMessage('error', 'Failed to delete board');
    }
}

/**
 * Open board in canvas view
 */
async function openBoard(boardId) {
    try {
        const response = await fetch(`/api/business-context/boards/${boardId}`);
        const data = await response.json();
        if (data.success) {
            currentBoard = data.board;
            
            // Save to localStorage for state persistence
            localStorage.setItem('business_context_last_board', boardId);
            
            switchToCanvasView();
            loadResources();
        } else {
            // Board not found or error - go back to list
            localStorage.setItem('business_context_last_board', 'list');
            loadBoards();
            showFlashMessage('error', data.error || 'Failed to load board');
        }
    } catch (error) {
        console.error('Error opening board:', error);
        localStorage.setItem('business_context_last_board', 'list');
        loadBoards();
        showFlashMessage('error', 'Failed to load board');
    }
}

/**
 * Switch to canvas view
 */
function switchToCanvasView() {
    document.getElementById('boardListView').style.display = 'none';
    document.getElementById('canvasView').style.display = 'flex';
    
    // Update board name
    document.getElementById('currentBoardName').textContent = currentBoard.name;
    
    // Wait for layout to settle before initializing canvas
    setTimeout(function() {
        if (!fabricCanvas) {
            initializeCanvas();
        }
    }, 50);
}

/**
 * Back to board list
 */
function backToList() {
    if (fabricCanvas) {
        fabricCanvas.dispose();
        fabricCanvas = null;
    }
    
    currentBoard = null;
    
    // Save to localStorage that we're on the list view
    localStorage.setItem('business_context_last_board', 'list');
    
    document.getElementById('canvasView').style.display = 'none';
    document.getElementById('boardListView').style.display = 'block';
    loadBoards();
}

/**
 * Initialize Fabric.js canvas
 */
function initializeCanvas() {
    const canvasEl = document.getElementById('canvas');
    const container = document.getElementById('canvasContainer');
    
    // Set initial canvas size (will be resized properly after init)
    const padding = 4; // 2px on each side = 4px total
    const initialWidth = Math.max(container.offsetWidth - padding, 100);
    const initialHeight = Math.max(container.offsetHeight - padding, 100);
    
    canvasEl.width = initialWidth;
    canvasEl.height = initialHeight;
    
    // Initialize Fabric canvas
    fabricCanvas = new fabric.Canvas('canvas', {
        backgroundColor: '#FFFFFF',
        selection: true,
        preserveObjectStacking: true,
        width: initialWidth,
        height: initialHeight
    });
    
    // Load canvas state if exists (for free objects only)
    if (currentBoard.canvas_state) {
        try {
            fabricCanvas.loadFromJSON(currentBoard.canvas_state, function() {
                // Remove group-related objects from canvas_state (they'll be loaded from database)
                const objectsToRemove = [];
                fabricCanvas.getObjects().forEach(obj => {
                    if (obj.objectType === 'group' || obj.objectType === 'groupText' || obj.objectType === 'groupCost') {
                        objectsToRemove.push(obj);
                    }
                });
                objectsToRemove.forEach(obj => fabricCanvas.remove(obj));
                
                // Now load groups from database (after clearing old ones from canvas_state)
                if (currentBoard.groups && currentBoard.groups.length > 0) {
                    loadGroupsOnCanvas(currentBoard.groups);
                }
                
                fabricCanvas.renderAll();
            });
        } catch (error) {
            console.error('Error loading canvas state:', error);
        }
    } else {
        // No canvas state, just load groups
        if (currentBoard.groups && currentBoard.groups.length > 0) {
            loadGroupsOnCanvas(currentBoard.groups);
        }
    }
    
    // Restore viewport
    if (currentBoard.viewport) {
        const viewport = currentBoard.viewport;
        fabricCanvas.setZoom(viewport.zoom || 1.0);
        fabricCanvas.absolutePan({ x: viewport.pan_x || 0, y: viewport.pan_y || 0 });
        updateZoomDisplay();
    }
    
    // Set up canvas event listeners
    setupCanvasEvents();
    
    // Set up canvas as drop zone for resources
    setupCanvasDropZone();
    
    // Initial resize to ensure proper dimensions - wait for DOM to settle
    requestAnimationFrame(function() {
        setTimeout(resizeCanvas, 50);
    });
    
    // Handle window resize with debounce
    let windowResizeTimeout;
    window.addEventListener('resize', function() {
        if (windowResizeTimeout) {
            clearTimeout(windowResizeTimeout);
        }
        windowResizeTimeout = setTimeout(function() {
            requestAnimationFrame(resizeCanvas);
        }, 150);
    });
    
    // Listen for InfraZen sidebar collapse/expand
    const appContainer = document.querySelector('.app-container');
    if (appContainer) {
        let sidebarResizeTimeout;
        const sidebarObserver = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'class') {
                    // Debounce resize
                    if (sidebarResizeTimeout) {
                        clearTimeout(sidebarResizeTimeout);
                    }
                    sidebarResizeTimeout = setTimeout(function() {
                        requestAnimationFrame(resizeCanvas);
                        sidebarResizeTimeout = null;
                    }, 350);
                }
            });
        });
        
        sidebarObserver.observe(appContainer, { attributes: true });
    }
}

/**
 * Setup canvas event listeners
 */
function setupCanvasEvents() {
    // Mouse wheel and touchpad gestures
    fabricCanvas.on('mouse:wheel', function(opt) {
        const evt = opt.e;
        
        // Check if it's a pinch gesture (ctrlKey is set on macOS trackpad pinch)
        if (evt.ctrlKey) {
            // PINCH TO ZOOM (macOS touchpad)
            const delta = evt.deltaY;
            let zoom = fabricCanvas.getZoom();
            zoom *= 0.99 ** delta;
            
            // Limit zoom
            if (zoom > 5) zoom = 5;
            if (zoom < 0.1) zoom = 0.1;
            
            fabricCanvas.zoomToPoint({ x: evt.offsetX, y: evt.offsetY }, zoom);
            updateZoomDisplay();
            scheduleAutoSave();
        } else {
            // 2-FINGER SCROLL TO PAN (macOS touchpad) or mouse wheel
            const deltaX = evt.deltaX || 0;
            const deltaY = evt.deltaY || 0;
            
            // Pan the canvas
            const vpt = fabricCanvas.viewportTransform;
            vpt[4] -= deltaX;
            vpt[5] -= deltaY;
            fabricCanvas.requestRenderAll();
            scheduleAutoSave();
        }
        
        evt.preventDefault();
        evt.stopPropagation();
    });
    
    // Miro-style panning: drag on empty space or hold space key
    let isPanning = false;
    let lastPosX, lastPosY;
    let spacePressed = false;
    
    // Track space key
    document.addEventListener('keydown', function(e) {
        if (e.code === 'Space' && !e.target.matches('input, textarea')) {
            spacePressed = true;
            if (fabricCanvas) {
                fabricCanvas.defaultCursor = 'grab';
            }
        }
    });
    
    document.addEventListener('keyup', function(e) {
        if (e.code === 'Space') {
            spacePressed = false;
            if (fabricCanvas && !isPanning) {
                fabricCanvas.defaultCursor = 'default';
            }
        }
    });
    
    fabricCanvas.on('mouse:down', function(opt) {
        const evt = opt.e;
        const target = opt.target;
        
        // Start panning if: middle mouse, space key, or clicking on empty canvas
        // On touchpad, this will be triggered by 2-finger drag
        if (evt.button === 1 || spacePressed || (!target && evt.button === 0)) {
            isPanning = true;
            fabricCanvas.selection = false;
            lastPosX = evt.clientX;
            lastPosY = evt.clientY;
            fabricCanvas.defaultCursor = 'grabbing';
            
            // Don't prevent default for touchpad to allow smooth scrolling
            if (evt.button !== 0 || spacePressed) {
                evt.preventDefault();
            }
        }
    });
    
    fabricCanvas.on('mouse:move', function(opt) {
        if (isPanning) {
            const evt = opt.e;
            const vpt = fabricCanvas.viewportTransform;
            vpt[4] += evt.clientX - lastPosX;
            vpt[5] += evt.clientY - lastPosY;
            fabricCanvas.requestRenderAll();
            lastPosX = evt.clientX;
            lastPosY = evt.clientY;
            
            scheduleAutoSave();
        }
    });
    
    fabricCanvas.on('mouse:up', function() {
        if (isPanning) {
            isPanning = false;
            fabricCanvas.selection = true;
            fabricCanvas.defaultCursor = spacePressed ? 'grab' : 'default';
        }
    });
    
    // Object modified - trigger autosave
    fabricCanvas.on('object:modified', function(e) {
        const obj = e.target;
        
        // If it's a group, update the database
        if (obj && obj.objectType === 'group') {
            updateGroupInDatabase(obj);
        }
        
        scheduleAutoSave();
    });
    
    fabricCanvas.on('object:added', function() {
        scheduleAutoSave();
    });
    
    fabricCanvas.on('object:removed', function() {
        scheduleAutoSave();
    });
    
    // Custom context menu
    setupContextMenu();
}

/**
 * Setup custom context menu
 */
function setupContextMenu() {
    const contextMenu = document.getElementById('contextMenu');
    let contextTarget = null;
    
    // Prevent default browser context menu and show custom one
    fabricCanvas.wrapperEl.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        
        // Get the object at mouse position
        const pointer = fabricCanvas.getPointer(e);
        const target = fabricCanvas.findTarget(e);
        
        // Show menu for groups, text, and rectangles
        if (target && (target.objectType === 'group' || target.objectType === 'freeText' || target.objectType === 'freeRect')) {
            contextTarget = target;
            
            // Show/hide menu items based on object type
            document.querySelectorAll('.context-menu-item').forEach(item => {
                const itemFor = item.dataset.for;
                if (itemFor) {
                    // Check if this item should be shown for this object type
                    const types = itemFor.split(',');
                    item.style.display = types.includes(target.objectType) ? 'flex' : 'none';
                }
            });
            
            // Position menu at mouse location
            contextMenu.style.left = e.clientX + 'px';
            contextMenu.style.top = e.clientY + 'px';
            contextMenu.style.display = 'block';
        } else {
            contextMenu.style.display = 'none';
        }
    });
    
    // Hide context menu when clicking elsewhere
    document.addEventListener('click', function() {
        contextMenu.style.display = 'none';
    });
    
    // Handle context menu actions
    document.querySelectorAll('.context-menu-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.stopPropagation();
            const action = this.dataset.action;
            
            if (!contextTarget) return;
            
            switch(action) {
                case 'rename':
                    const groupText = fabricCanvas.getObjects().find(obj => 
                        obj.objectType === 'groupText' && obj.parentFabricId === contextTarget.fabricId
                    );
                    editGroupName(contextTarget, groupText);
                    break;
                    
                case 'change-color':
                    changeGroupColor(contextTarget);
                    break;
                
                case 'properties':
                    // Show properties panel for free objects
                    showPropertiesPanel(contextTarget);
                    fabricCanvas.setActiveObject(contextTarget);
                    fabricCanvas.renderAll();
                    break;
                    
                case 'delete':
                    if (contextTarget.objectType === 'group') {
                        deleteGroup(contextTarget);
                    } else if (contextTarget.objectType === 'freeText' || contextTarget.objectType === 'freeRect') {
                        fabricCanvas.remove(contextTarget);
                        fabricCanvas.renderAll();
                        hidePropertiesPanel();
                        scheduleAutoSave();
                    }
                    break;
            }
            
            contextMenu.style.display = 'none';
            contextTarget = null;
        });
    });
}

/**
 * Resize canvas to fit container
 */
function resizeCanvas() {
    if (!fabricCanvas) return;
    
    const container = document.getElementById('canvasContainer');
    if (!container) return;
    
    // Get actual container dimensions
    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;
    
    // Account for padding (2px on each side = 4px total)
    const padding = 4;
    const width = Math.max(containerWidth - padding, 100);
    const height = Math.max(containerHeight - padding, 100);
    
    // Update canvas element size
    const canvasEl = document.getElementById('canvas');
    if (canvasEl) {
        canvasEl.width = width;
        canvasEl.height = height;
    }
    
    // Update Fabric canvas dimensions
    fabricCanvas.setWidth(width);
    fabricCanvas.setHeight(height);
    fabricCanvas.calcOffset();
    fabricCanvas.renderAll();
}

/**
 * Zoom controls
 */
function zoomIn() {
    if (!fabricCanvas) return;
    let zoom = fabricCanvas.getZoom();
    zoom = Math.min(zoom * 1.1, 5);
    fabricCanvas.setZoom(zoom);
    updateZoomDisplay();
    scheduleAutoSave();
}

function zoomOut() {
    if (!fabricCanvas) return;
    let zoom = fabricCanvas.getZoom();
    zoom = Math.max(zoom * 0.9, 0.1);
    fabricCanvas.setZoom(zoom);
    updateZoomDisplay();
    scheduleAutoSave();
}

function zoomReset() {
    if (!fabricCanvas) return;
    fabricCanvas.setZoom(1);
    fabricCanvas.absolutePan({ x: 0, y: 0 });
    updateZoomDisplay();
    scheduleAutoSave();
}

function updateZoomDisplay() {
    if (!fabricCanvas) return;
    const zoom = Math.round(fabricCanvas.getZoom() * 100);
    document.getElementById('zoomLevel').textContent = zoom + '%';
}

/**
 * Toggle toolbox visibility
 */
function toggleToolbox() {
    const toolbox = document.getElementById('toolbox');
    const wasHidden = toolbox.classList.contains('hidden');
    toolbox.classList.toggle('hidden');
    
    // Resize canvas after toolbox animation completes (if needed)
    // Canvas is now full-width regardless, but this ensures proper rendering
    if (fabricCanvas) {
        setTimeout(function() {
            fabricCanvas.calcOffset();
            fabricCanvas.renderAll();
        }, 300);
    }
}

/**
 * Load available resources
 */
async function loadResources() {
    try {
        const response = await fetch('/api/business-context/available-resources');
        const data = await response.json();
        
        if (data.success) {
            allResources = data.resources;
            displayResources();
            
            // Update unplaced badge
            document.getElementById('unplacedBadge').textContent = data.unplaced_count;
        } else {
            showFlashMessage('error', data.error || 'Failed to load resources');
        }
    } catch (error) {
        console.error('Error loading resources:', error);
        showFlashMessage('error', 'Failed to load resources');
    }
}

/**
 * Display resources in toolbox
 */
function displayResources() {
    const resourcesList = document.getElementById('resourcesList');
    
    if (!allResources || allResources.length === 0) {
        resourcesList.innerHTML = '<div class="empty-state"><p>No resources available</p></div>';
        return;
    }
    
    const html = allResources.map(provider => `
        <div class="resource-provider-group">
            <div class="resource-provider-header">
                <i class="fa-solid fa-cloud"></i>
                <span>${escapeHtml(provider.provider_name)} (${provider.resources.length})</span>
            </div>
            ${provider.resources.map(resource => `
                <div class="resource-item ${resource.is_placed ? 'placed' : ''}" 
                     data-resource-id="${resource.id}"
                     draggable="${!resource.is_placed}">
                    <div class="resource-icon">
                        <i class="fa-solid fa-server"></i>
                        <div class="resource-info-icon" onclick="showResourceInfo(${resource.id})">
                            <i class="fa-solid fa-info"></i>
                        </div>
                        <div class="resource-notes-icon ${resource.has_notes ? 'has-notes' : ''}" 
                             onclick="showResourceNotes(${resource.id})">
                            <i class="fa-solid fa-note-sticky"></i>
                        </div>
                    </div>
                    <div class="resource-details">
                        <div class="resource-name">${escapeHtml(resource.name)}</div>
                        <div class="resource-meta">${resource.type} • ${resource.ip || 'No IP'}</div>
                    </div>
                    ${resource.is_placed ? '<span class="resource-badge">Placed</span>' : ''}
                </div>
            `).join('')}
        </div>
    `).join('');
    
    resourcesList.innerHTML = html;
    
    // Set up drag event listeners for resources
    setupResourceDragListeners();
}

/**
 * Setup drag listeners for resource items
 */
function setupResourceDragListeners() {
    const resourceItems = document.querySelectorAll('.resource-item[draggable="true"]');
    
    resourceItems.forEach(item => {
        item.addEventListener('dragstart', function(e) {
            const resourceId = parseInt(this.dataset.resourceId);
            e.dataTransfer.setData('text/plain', resourceId);
            e.dataTransfer.effectAllowed = 'copy';
            
            // Add dragging class for visual feedback
            this.classList.add('dragging');
        });
        
        item.addEventListener('dragend', function(e) {
            this.classList.remove('dragging');
        });
    });
}

/**
 * Setup canvas drop zone for resources
 */
function setupCanvasDropZone() {
    if (!fabricCanvas) return;
    
    const canvasElement = fabricCanvas.wrapperEl;
    
    // Prevent default drag behavior
    canvasElement.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    });
    
    // Handle drop
    canvasElement.addEventListener('drop', async function(e) {
        e.preventDefault();
        
        const resourceId = e.dataTransfer.getData('text/plain');
        if (!resourceId) return;
        
        // Get drop position relative to canvas
        const rect = canvasElement.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Convert screen coordinates to canvas coordinates
        const pointer = fabricCanvas.getPointer(e);
        
        await placeResourceOnCanvas(parseInt(resourceId), pointer.x, pointer.y);
    });
}

/**
 * Place resource on canvas
 */
async function placeResourceOnCanvas(resourceId, x, y) {
    if (!currentBoard) {
        showFlashMessage('error', 'Откройте доску');
        return;
    }
    
    // Find resource data
    let resourceData = null;
    for (const provider of allResources) {
        const found = provider.resources.find(r => r.id === resourceId);
        if (found) {
            resourceData = found;
            break;
        }
    }
    
    if (!resourceData) {
        showFlashMessage('error', 'Ресурс не найден');
        return;
    }
    
    // Check if already placed
    if (resourceData.is_placed) {
        showFlashMessage('error', 'Ресурс уже размещен на доске');
        return;
    }
    
    try {
        // Check if dropped inside a group
        const groupId = getGroupAtPosition(x, y);
        
        // Save to database
        const response = await fetch(`/api/business-context/boards/${currentBoard.id}/resources`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resource_id: resourceId,
                position_x: x,
                position_y: y,
                group_id: groupId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Create Fabric.js object for resource
            createResourceObject(resourceData, x, y, data.board_resource.id, groupId);
            
            // Update resource status in toolbox
            resourceData.is_placed = true;
            displayResources();
            
            // Reload resources to update counts
            await loadAvailableResources();
            
            // If placed in group, update group cost
            if (groupId) {
                await updateGroupCost(groupId);
            }
            
            scheduleAutoSave();
        } else {
            showFlashMessage('error', data.error || 'Ошибка размещения ресурса');
        }
    } catch (error) {
        console.error('Error placing resource:', error);
        showFlashMessage('error', 'Ошибка размещения ресурса');
    }
}

/**
 * Create Fabric.js object for resource on canvas
 */
function createResourceObject(resourceData, x, y, boardResourceId, groupId) {
    // Create resource container group
    const resourceIcon = new fabric.Rect({
        width: 120,
        height: 80,
        fill: '#FFFFFF',
        stroke: '#E5E7EB',
        strokeWidth: 1,
        rx: 8,
        ry: 8
    });
    
    // Resource name text
    const nameText = new fabric.Text(resourceData.name, {
        fontSize: 14,
        fontWeight: 'bold',
        fill: '#1F2937',
        originX: 'center',
        originY: 'top'
    });
    
    // Resource type and IP text
    const metaText = new fabric.Text(`${resourceData.type}\n${resourceData.ip || 'No IP'}`, {
        fontSize: 11,
        fill: '#6B7280',
        originX: 'center',
        originY: 'top',
        textAlign: 'center'
    });
    
    // Create group
    const resourceGroup = new fabric.Group([resourceIcon, nameText, metaText], {
        left: x - 60,
        top: y - 40,
        selectable: true,
        hasControls: false,
        hasBorders: true,
        lockRotation: true,
        objectType: 'resource',
        resourceId: resourceData.id,
        boardResourceId: boardResourceId,
        groupId: groupId,
        resourceData: resourceData,
        // Preserve custom properties
        toObject: (function(toObject) {
            return function() {
                return fabric.util.object.extend(toObject.call(this), {
                    objectType: this.objectType,
                    resourceId: this.resourceId,
                    boardResourceId: this.boardResourceId,
                    groupId: this.groupId
                });
            };
        })(fabric.Group.prototype.toObject)
    });
    
    // Position children within group
    nameText.set({ top: -30 });
    metaText.set({ top: -5 });
    
    // Add to canvas
    fabricCanvas.add(resourceGroup);
    fabricCanvas.renderAll();
    
    // Setup event handlers
    resourceGroup.on('moving', function() {
        // Check if moved into/out of groups
        checkResourceGroupAssignment(this);
    });
    
    resourceGroup.on('modified', function() {
        // Save new position to database
        updateResourcePosition(this);
    });
}

/**
 * Get group at specific position (for drop detection)
 */
function getGroupAtPosition(x, y) {
    const objects = fabricCanvas.getObjects();
    
    for (const obj of objects) {
        if (obj.objectType === 'group') {
            const bounds = obj.getBoundingRect();
            if (x >= bounds.left && x <= bounds.left + bounds.width &&
                y >= bounds.top && y <= bounds.top + bounds.height) {
                return obj.dbId;
            }
        }
    }
    
    return null;
}

/**
 * Check if resource should be assigned to a group
 */
function checkResourceGroupAssignment(resourceObj) {
    const center = resourceObj.getCenterPoint();
    const newGroupId = getGroupAtPosition(center.x, center.y);
    
    if (newGroupId !== resourceObj.groupId) {
        const oldGroupId = resourceObj.groupId;
        resourceObj.groupId = newGroupId;
        
        // Update database and group costs
        updateResourceGroupAssignment(resourceObj.boardResourceId, newGroupId, oldGroupId);
    }
}

/**
 * Update resource position in database
 */
async function updateResourcePosition(resourceObj) {
    if (!resourceObj.boardResourceId) return;
    
    try {
        await fetch(`/api/business-context/resources/${resourceObj.boardResourceId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                position_x: resourceObj.left,
                position_y: resourceObj.top
            })
        });
    } catch (error) {
        console.error('Error updating resource position:', error);
    }
}

/**
 * Update resource group assignment
 */
async function updateResourceGroupAssignment(boardResourceId, newGroupId, oldGroupId) {
    try {
        await fetch(`/api/business-context/resources/${boardResourceId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                group_id: newGroupId
            })
        });
        
        // Update costs for affected groups
        if (oldGroupId) await updateGroupCost(oldGroupId);
        if (newGroupId) await updateGroupCost(newGroupId);
        
    } catch (error) {
        console.error('Error updating resource group assignment:', error);
    }
}

/**
 * Update group cost badge
 */
async function updateGroupCost(groupDbId) {
    try {
        const response = await fetch(`/api/business-context/groups/${groupDbId}/cost`);
        const data = await response.json();
        
        if (data.success) {
            // Find group object on canvas and update cost display
            const objects = fabricCanvas.getObjects();
            for (const obj of objects) {
                if (obj.objectType === 'group' && obj.dbId === groupDbId) {
                    obj.calculatedCost = data.cost;
                    
                    // Update cost badge text
                    const costBadgeText = objects.find(o => 
                        o.objectType === 'groupCost' && o.parentFabricId === obj.fabricId
                    );
                    if (costBadgeText) {
                        const costText = data.cost > 0 ? `${data.cost.toFixed(2)} ₽/день` : '0 ₽/день';
                        costBadgeText.set('text', costText);
                    }
                    
                    fabricCanvas.renderAll();
                    break;
                }
            }
        }
    } catch (error) {
        console.error('Error updating group cost:', error);
    }
}

/**
 * Filter resources
 */
function filterResources() {
    const searchTerm = document.getElementById('resourceSearch').value.toLowerCase();
    const items = document.querySelectorAll('.resource-item');
    
    items.forEach(item => {
        const resourceName = item.querySelector('.resource-name').textContent.toLowerCase();
        const resourceMeta = item.querySelector('.resource-meta').textContent.toLowerCase();
        const isPlaced = item.classList.contains('placed');
        
        let showByFilter = true;
        if (currentFilter === 'placed') showByFilter = isPlaced;
        if (currentFilter === 'unplaced') showByFilter = !isPlaced;
        
        const showBySearch = resourceName.includes(searchTerm) || resourceMeta.includes(searchTerm);
        
        item.style.display = (showByFilter && showBySearch) ? 'flex' : 'none';
    });
}

/**
 * Show resource info modal
 */
function showResourceInfo(resourceId) {
    // TODO: Implement in Phase 5
    alert('Информация о ресурсе - Скоро будет доступно');
}

/**
 * Show resource notes modal
 */
function showResourceNotes(resourceId) {
    // TODO: Implement in Phase 5
    alert('Заметки о ресурсе - Скоро будет доступно');
}

/**
 * Close resource info modal
 */
function closeResourceInfoModal() {
    document.getElementById('resourceInfoModal').classList.remove('active');
}

/**
 * Close resource notes modal
 */
function closeResourceNotesModal() {
    document.getElementById('resourceNotesModal').classList.remove('active');
}

/**
 * Save resource notes
 */
function saveResourceNotes() {
    // TODO: Implement in Phase 5
    closeResourceNotesModal();
}

/**
 * Update board name
 */
async function updateBoardName(newName) {
    if (!currentBoard || !newName) return;
    
    try {
        const response = await fetch(`/api/business-context/boards/${currentBoard.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentBoard.name = newName;
            showFlashMessage('success', 'Board name updated');
        } else {
            showFlashMessage('error', data.error || 'Failed to update board name');
            document.getElementById('currentBoardName').textContent = currentBoard.name;
        }
    } catch (error) {
        console.error('Error updating board name:', error);
        showFlashMessage('error', 'Failed to update board name');
        document.getElementById('currentBoardName').textContent = currentBoard.name;
    }
}

/**
 * Schedule auto-save
 */
function scheduleAutoSave() {
    const indicator = document.getElementById('saveIndicator');
    indicator.textContent = 'Изменения...';
    indicator.className = 'save-indicator saving';
    
    if (autoSaveTimer) {
        clearTimeout(autoSaveTimer);
    }
    
    autoSaveTimer = setTimeout(() => {
        saveBoard(true);
    }, 3000); // 3 seconds debounce
}

/**
 * Save board
 */
async function saveBoard(isAutoSave = false) {
    if (!currentBoard || !fabricCanvas) return;
    
    const indicator = document.getElementById('saveIndicator');
    
    if (!isAutoSave) {
        indicator.textContent = 'Сохранение...';
        indicator.className = 'save-indicator saving';
    }
    
    const canvasState = fabricCanvas.toJSON();
    const viewport = {
        zoom: fabricCanvas.getZoom(),
        pan_x: fabricCanvas.viewportTransform[4],
        pan_y: fabricCanvas.viewportTransform[5]
    };
    
    try {
        const response = await fetch(`/api/business-context/boards/${currentBoard.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                canvas_state: canvasState,
                viewport: viewport
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            indicator.textContent = 'Сохранено';
            indicator.className = 'save-indicator saved';
            
            if (!isAutoSave) {
                showFlashMessage('success', 'Board saved successfully');
            }
        } else {
            indicator.textContent = 'Ошибка';
            indicator.className = 'save-indicator';
            showFlashMessage('error', data.error || 'Failed to save board');
        }
    } catch (error) {
        console.error('Error saving board:', error);
        indicator.textContent = 'Ошибка';
        indicator.className = 'save-indicator';
        showFlashMessage('error', 'Failed to save board');
    }
}

/**
 * Create a new group on canvas
 */
async function createGroupOnCanvas() {
    if (!fabricCanvas || !currentBoard) return;
    
    // Generate unique fabric_id
    const fabricId = 'group_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // Get canvas center position
    const zoom = fabricCanvas.getZoom();
    const vpt = fabricCanvas.viewportTransform;
    const centerX = (fabricCanvas.width / 2 - vpt[4]) / zoom;
    const centerY = (fabricCanvas.height / 2 - vpt[5]) / zoom;
    
    // Create group rectangle
    const groupRect = new fabric.Rect({
        left: centerX - 150,
        top: centerY - 100,
        width: 300,
        height: 200,
        fill: 'rgba(59, 130, 246, 0.05)',
        stroke: '#3B82F6',
        strokeWidth: 2,
        rx: 4,
        ry: 4,
        selectable: true,
        hasControls: true,
        hasBorders: true,
        objectType: 'group',
        fabricId: fabricId,
        groupName: 'Новая группа',
        groupColor: '#3B82F6',
        calculatedCost: 0,
        // Make sure Fabric.js preserves our custom properties
        toObject: (function(toObject) {
            return function() {
                return fabric.util.object.extend(toObject.call(this), {
                    objectType: this.objectType,
                    fabricId: this.fabricId,
                    groupName: this.groupName,
                    groupColor: this.groupColor,
                    calculatedCost: this.calculatedCost,
                    dbId: this.dbId
                });
            };
        })(fabric.Rect.prototype.toObject)
    });
    
    // Create group name text
    const groupText = new fabric.Text('Новая группа', {
        left: centerX - 140,
        top: centerY - 90,
        fontSize: 16,
        fontWeight: 'bold',
        fill: '#1F2937',
        selectable: false,
        evented: false,
        objectType: 'groupText',
        parentFabricId: fabricId,
        // Preserve custom properties in JSON
        toObject: (function(toObject) {
            return function() {
                return fabric.util.object.extend(toObject.call(this), {
                    objectType: this.objectType,
                    parentFabricId: this.parentFabricId
                });
            };
        })(fabric.Text.prototype.toObject)
    });
    
    // Create cost badge text
    const costBadge = new fabric.Text('0 ₽/день', {
        left: centerX + 100,
        top: centerY - 90,
        fontSize: 14,
        fontWeight: '600',
        fill: '#10B981',
        selectable: false,
        evented: false,
        objectType: 'groupCost',
        parentFabricId: fabricId,
        // Preserve custom properties in JSON
        toObject: (function(toObject) {
            return function() {
                return fabric.util.object.extend(toObject.call(this), {
                    objectType: this.objectType,
                    parentFabricId: this.parentFabricId
                });
            };
        })(fabric.Text.prototype.toObject)
    });
    
    // Add objects to canvas
    fabricCanvas.add(groupRect);
    fabricCanvas.add(groupText);
    fabricCanvas.add(costBadge);
    
    // Make text and badge move with the group
    groupRect.on('moving', function() {
        updateGroupChildren(groupRect, groupText, costBadge);
    });
    
    groupRect.on('scaling', function() {
        const newWidth = groupRect.width * groupRect.scaleX;
        const newHeight = groupRect.height * groupRect.scaleY;
        
        groupRect.set({
            width: newWidth,
            height: newHeight,
            scaleX: 1,
            scaleY: 1
        });
        
        updateGroupChildren(groupRect, groupText, costBadge);
    });
    
    groupRect.on('modified', function() {
        updateGroupInDatabase(groupRect);
    });
    
    // Double-click to edit name
    groupRect.on('mousedblclick', function() {
        editGroupName(groupRect, groupText);
    });
    
    fabricCanvas.renderAll();
    
    // Save group to database
    await saveGroupToDatabase(groupRect);
    
    scheduleAutoSave();
}

/**
 * Create text object on canvas
 */
function createTextOnCanvas() {
    if (!fabricCanvas || !currentBoard) return;
    
    // Get canvas center position
    const zoom = fabricCanvas.getZoom();
    const vpt = fabricCanvas.viewportTransform;
    const centerX = (fabricCanvas.width / 2 - vpt[4]) / zoom;
    const centerY = (fabricCanvas.height / 2 - vpt[5]) / zoom;
    
    // Create text object
    const text = new fabric.IText('Текст', {
        left: centerX - 50,
        top: centerY - 20,
        fontSize: 24,
        fontFamily: 'Arial, sans-serif',
        fill: '#1F2937',
        objectType: 'freeText',
        selectable: true,
        editable: true
    });
    
    // Add to canvas
    fabricCanvas.add(text);
    fabricCanvas.setActiveObject(text);
    
    // Enter edit mode immediately
    text.enterEditing();
    text.selectAll();
    
    fabricCanvas.renderAll();
    scheduleAutoSave();
}

/**
 * Create rectangle object on canvas
 */
function createRectangleOnCanvas() {
    if (!fabricCanvas || !currentBoard) return;
    
    // Get canvas center position
    const zoom = fabricCanvas.getZoom();
    const vpt = fabricCanvas.viewportTransform;
    const centerX = (fabricCanvas.width / 2 - vpt[4]) / zoom;
    const centerY = (fabricCanvas.height / 2 - vpt[5]) / zoom;
    
    // Create rectangle object
    const rect = new fabric.Rect({
        left: centerX - 100,
        top: centerY - 60,
        width: 200,
        height: 120,
        fill: 'rgba(59, 130, 246, 0.2)',
        stroke: '#3B82F6',
        strokeWidth: 2,
        rx: 4,
        ry: 4,
        objectType: 'freeRect',
        selectable: true,
        hasControls: true,
        hasBorders: true
    });
    
    // Add to canvas
    fabricCanvas.add(rect);
    fabricCanvas.setActiveObject(rect);
    
    fabricCanvas.renderAll();
    scheduleAutoSave();
}

/**
 * Load groups from board data and render on canvas
 */
function loadGroupsOnCanvas(groups) {
    if (!fabricCanvas || !groups) {
        return;
    }
    
    groups.forEach(group => {
        try {
            // Create group rectangle
            const groupRect = new fabric.Rect({
            left: group.position.x,
            top: group.position.y,
            width: group.size.width,
            height: group.size.height,
            fill: hexToRgba(group.color, 0.05),
            stroke: group.color,
            strokeWidth: 2,
            rx: 4,
            ry: 4,
            selectable: true,
            hasControls: true,
            hasBorders: true,
            objectType: 'group',
            fabricId: group.fabric_id,
            groupName: group.name,
            groupColor: group.color,
            calculatedCost: group.calculated_cost || 0,
            dbId: group.id,
            // Make sure Fabric.js preserves our custom properties
            toObject: (function(toObject) {
                return function() {
                    return fabric.util.object.extend(toObject.call(this), {
                        objectType: this.objectType,
                        fabricId: this.fabricId,
                        groupName: this.groupName,
                        groupColor: this.groupColor,
                        calculatedCost: this.calculatedCost,
                        dbId: this.dbId
                    });
                };
            })(fabric.Rect.prototype.toObject)
        });
        
        // Create group name text
        const groupText = new fabric.Text(group.name, {
            left: group.position.x + 10,
            top: group.position.y + 10,
            fontSize: 16,
            fontWeight: 'bold',
            fill: '#1F2937',
            selectable: false,
            evented: false,
            objectType: 'groupText',
            parentFabricId: group.fabric_id,
            // Preserve custom properties in JSON
            toObject: (function(toObject) {
                return function() {
                    return fabric.util.object.extend(toObject.call(this), {
                        objectType: this.objectType,
                        parentFabricId: this.parentFabricId
                    });
                };
            })(fabric.Text.prototype.toObject)
        });
        
        // Create cost badge text
        const costText = group.calculated_cost > 0 ? `${group.calculated_cost.toFixed(2)} ₽/день` : '0 ₽/день';
        const costBadge = new fabric.Text(costText, {
            left: group.position.x + group.size.width - 80,
            top: group.position.y + 10,
            fontSize: 14,
            fontWeight: '600',
            fill: '#10B981',
            selectable: false,
            evented: false,
            objectType: 'groupCost',
            parentFabricId: group.fabric_id,
            // Preserve custom properties in JSON
            toObject: (function(toObject) {
                return function() {
                    return fabric.util.object.extend(toObject.call(this), {
                        objectType: this.objectType,
                        parentFabricId: this.parentFabricId
                    });
                };
            })(fabric.Text.prototype.toObject)
        });
        
        // Add to canvas
        fabricCanvas.add(groupRect);
        fabricCanvas.add(groupText);
        fabricCanvas.add(costBadge);
        
        // Setup event handlers
        groupRect.on('moving', function() {
            updateGroupChildren(groupRect, groupText, costBadge);
        });
        
        groupRect.on('scaling', function() {
            const newWidth = groupRect.width * groupRect.scaleX;
            const newHeight = groupRect.height * groupRect.scaleY;
            
            groupRect.set({
                width: newWidth,
                height: newHeight,
                scaleX: 1,
                scaleY: 1
            });
            
            updateGroupChildren(groupRect, groupText, costBadge);
        });
        
        groupRect.on('modified', function() {
            updateGroupInDatabase(groupRect);
        });
        
        groupRect.on('mousedblclick', function() {
            editGroupName(groupRect, groupText);
        });
        } catch (error) {
            console.error('Error loading group:', error);
        }
    });
    
    fabricCanvas.renderAll();
}

/**
 * Update group children (text and cost badge) position
 */
function updateGroupChildren(groupRect, groupText, costBadge) {
    groupText.set({
        left: groupRect.left + 10,
        top: groupRect.top + 10
    });
    costBadge.set({
        left: groupRect.left + groupRect.width - 80,
        top: groupRect.top + 10
    });
    fabricCanvas.renderAll();
}

/**
 * Edit group name
 */
function editGroupName(groupRect, groupText) {
    const currentName = groupRect.groupName || 'Новая группа';
    const newName = prompt('Введите название группы:', currentName);
    
    if (newName && newName.trim()) {
        groupRect.groupName = newName.trim();
        groupText.set('text', newName.trim());
        fabricCanvas.renderAll();
        
        // Update in database
        updateGroupInDatabase(groupRect);
        scheduleAutoSave();
    }
}

/**
 * Change group color
 */
function changeGroupColor(groupRect) {
    const colors = [
        { name: 'Синий', value: '#3B82F6' },
        { name: 'Зелёный', value: '#10B981' },
        { name: 'Фиолетовый', value: '#8B5CF6' },
        { name: 'Оранжевый', value: '#F59E0B' },
        { name: 'Красный', value: '#EF4444' },
        { name: 'Розовый', value: '#EC4899' },
        { name: 'Серый', value: '#6B7280' }
    ];
    
    const colorOptions = colors.map((c, i) => `${i + 1}. ${c.name}`).join('\n');
    const choice = prompt(`Выберите цвет (1-${colors.length}):\n\n${colorOptions}`);
    
    const index = parseInt(choice) - 1;
    if (index >= 0 && index < colors.length) {
        const newColor = colors[index].value;
        groupRect.groupColor = newColor;
        groupRect.set({
            stroke: newColor,
            fill: hexToRgba(newColor, 0.05)
        });
        fabricCanvas.renderAll();
        
        // Update in database
        updateGroupInDatabase(groupRect);
        scheduleAutoSave();
    }
}

/**
 * Update group in database when modified
 */
async function updateGroupInDatabase(groupRect) {
    if (!currentBoard || !groupRect.dbId) return;
    
    try {
        const response = await fetch(`/api/business-context/groups/${groupRect.dbId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                position_x: groupRect.left,
                position_y: groupRect.top,
                width: groupRect.width,
                height: groupRect.height,
                color: groupRect.groupColor || '#3B82F6'
            })
        });
        
        const data = await response.json();
        if (!data.success) {
            console.error('Failed to update group in database:', data.error);
        }
    } catch (error) {
        console.error('Error updating group in database:', error);
    }
}

/**
 * Save group to database
 */
async function saveGroupToDatabase(groupRect) {
    if (!currentBoard) return;
    
    try {
        const response = await fetch(`/api/business-context/boards/${currentBoard.id}/groups`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: groupRect.groupName,
                fabric_id: groupRect.fabricId,
                position_x: groupRect.left,
                position_y: groupRect.top,
                width: groupRect.width,
                height: groupRect.height,
                color: groupRect.groupColor || '#3B82F6'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            groupRect.dbId = data.group.id;
        } else {
            showFlashMessage('error', data.error || 'Failed to save group');
        }
    } catch (error) {
        console.error('Error saving group:', error);
        showFlashMessage('error', 'Failed to save group');
    }
}

/**
 * Update group in database
 */
async function updateGroupInDatabase(groupRect) {
    if (!currentBoard || !groupRect.dbId) return;
    
    try {
        const response = await fetch(`/api/business-context/groups/${groupRect.dbId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: groupRect.groupName,
                position_x: groupRect.left,
                position_y: groupRect.top,
                width: groupRect.width,
                height: groupRect.height,
                color: groupRect.groupColor || '#3B82F6'
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            console.error('Failed to update group:', data.error);
        }
    } catch (error) {
        console.error('Error updating group:', error);
    }
}

/**
 * Delete group
 */
async function deleteGroup(groupRect) {
    if (!groupRect.dbId) return;
    
    if (!confirm('Удалить группу?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/business-context/groups/${groupRect.dbId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Remove from canvas
            const objects = fabricCanvas.getObjects();
            objects.forEach(obj => {
                if (obj.fabricId === groupRect.fabricId || obj.parentFabricId === groupRect.fabricId) {
                    fabricCanvas.remove(obj);
                }
            });
            fabricCanvas.renderAll();
            scheduleAutoSave();
        } else {
            showFlashMessage('error', data.error || 'Failed to delete group');
        }
    } catch (error) {
        console.error('Error deleting group:', error);
        showFlashMessage('error', 'Failed to delete group');
    }
}

/**
 * Check if a resource is inside a group (containment detection)
 * This will be used when implementing resource placement in Phase 5
 */
function getContainingGroup(resourceX, resourceY) {
    if (!fabricCanvas) return null;
    
    const groups = fabricCanvas.getObjects().filter(obj => obj.objectType === 'group');
    
    for (let group of groups) {
        const left = group.left;
        const top = group.top;
        const right = left + group.width;
        const bottom = top + group.height;
        
        if (resourceX >= left && resourceX <= right && resourceY >= top && resourceY <= bottom) {
            return group;
        }
    }
    
    return null;
}

/**
 * Recalculate and update group cost
 * Will be fully implemented in Phase 5 when resources can be placed
 */
async function recalculateGroupCost(groupId) {
    if (!groupId) return;
    
    try {
        const response = await fetch(`/api/business-context/groups/${groupId}/cost`);
        const data = await response.json();
        
        if (data.success) {
            // Find the group on canvas and update its cost badge
            const groups = fabricCanvas.getObjects().filter(obj => obj.objectType === 'group' && obj.dbId === groupId);
            if (groups.length > 0) {
                const groupRect = groups[0];
                groupRect.calculatedCost = data.calculated_cost;
                
                // Find and update cost badge
                const costBadge = fabricCanvas.getObjects().find(obj => 
                    obj.objectType === 'groupCost' && obj.parentFabricId === groupRect.fabricId
                );
                
                if (costBadge) {
                    const costText = data.calculated_cost > 0 ? 
                        `${data.calculated_cost.toFixed(2)} ₽/день` : '0 ₽/день';
                    costBadge.set('text', costText);
                    fabricCanvas.renderAll();
                }
            }
        }
    } catch (error) {
        console.error('Error recalculating group cost:', error);
    }
}

/**
 * Utility: Convert hex color to rgba
 */
function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Utility: Escape HTML
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Setup keyboard shortcuts
 */
document.addEventListener('keydown', function(e) {
    if (!fabricCanvas) return;
    
    // Delete key - delete selected object
    if (e.key === 'Delete' || e.key === 'Backspace') {
        const activeObject = fabricCanvas.getActiveObject();
        if (activeObject && activeObject.objectType === 'group') {
            e.preventDefault();
            deleteGroup(activeObject);
        }
    }
    
    // Ctrl/Cmd + S - Save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveBoard(false);
    }
});

/**
 * Show flash message
 */
function showFlashMessage(type, message) {
    // Use existing flash message system from main.js if available
    if (typeof window.showMessage === 'function') {
        window.showMessage(type, message);
    } else {
        alert(message);
    }
}

