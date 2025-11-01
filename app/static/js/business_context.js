/**
 * Business Context - Visual Resource Mapping
 * 
 * This module handles the visual board interface for mapping cloud resources
 * to business contexts (customers, features, departments, etc.)
 */

/**
 * Custom Fabric.js class for Resource Cards
 * This is a monolithic object that manages all its child elements (card, text, badges)
 * Separate from fabric.Group used for business context containers
 */
fabric.ResourceCard = fabric.util.createClass(fabric.Group, {
    type: 'resourceCard',
    
    initialize: function(resourceData, options) {
        options = options || {};
        
        const cardWidth = 120;
        const cardHeight = 80;
        
        // Create all child elements with relative positions
        const elements = [];
        
        // 1. Main card rectangle
        elements.push(new fabric.Rect({
            left: 0,
            top: 0,
            width: cardWidth,
            height: cardHeight,
            fill: '#FFFFFF',
            stroke: '#E5E7EB',
            strokeWidth: 2,
            rx: 8,
            ry: 8
        }));
        
        // 2. Resource name text
        elements.push(new fabric.Text(resourceData.name, {
            left: cardWidth / 2,
            top: 15,
            fontSize: 13,
            fontWeight: 'bold',
            fill: '#1F2937',
            originX: 'center',
            originY: 'top'
        }));
        
        // 3. Resource type/IP text
        elements.push(new fabric.Text(`${resourceData.type || 'Resource'}\n${resourceData.ip || 'No IP'}`, {
            left: cardWidth / 2,
            top: 40,
            fontSize: 10,
            fill: '#6B7280',
            originX: 'center',
            originY: 'top',
            textAlign: 'center'
        }));
        
        // 4. Info icon circle (solid blue badge)
        elements.push(new fabric.Circle({
            left: 10,
            top: 10,
            radius: 10,
            fill: '#3B82F6',
            originX: 'center',
            originY: 'center'
        }));
        
        // 5. Info icon text (white 'i' on blue)
        elements.push(new fabric.Text('i', {
            left: 10,
            top: 10,
            fontSize: 12,
            fontWeight: 'bold',
            fill: '#FFFFFF',
            originX: 'center',
            originY: 'center'
        }));
        
        // 6. Notes icon circle (solid green badge when has notes)
        const hasNotes = resourceData.has_notes || (resourceData.notes && resourceData.notes.trim().length > 0);
        elements.push(new fabric.Circle({
            left: cardWidth - 10,
            top: 10,
            radius: 10,
            fill: hasNotes ? '#10B981' : '#9CA3AF',
            originX: 'center',
            originY: 'center'
        }));
        
        // 7. Notes icon text (white 'n' on colored background)
        elements.push(new fabric.Text('n', {
            left: cardWidth - 10,
            top: 10,
            fontSize: 12,
            fontWeight: 'bold',
            fill: '#FFFFFF',
            originX: 'center',
            originY: 'center'
        }));
        
        // 8. Clone badge circle (initially hidden, solid purple badge)
        elements.push(new fabric.Circle({
            left: cardWidth - 10,
            top: cardHeight - 10,
            radius: 10,
            fill: '#8B5CF6',
            originX: 'center',
            originY: 'center',
            visible: false
        }));
        
        // 9. Clone badge text (initially hidden, white 'c' on purple)
        elements.push(new fabric.Text('c', {
            left: cardWidth - 10,
            top: cardHeight - 10,
            fontSize: 12,
            fontWeight: 'bold',
            fill: '#FFFFFF',
            originX: 'center',
            originY: 'center',
            visible: false
        }));
        
        // Call parent constructor
        this.callSuper('initialize', elements, {
            ...options,
            subTargetCheck: true,
            interactive: true,
            lockRotation: true,
            hasRotate: false,
            hasControls: false,
            hasBorders: true
        });
        
        // Store custom properties
        this.objectType = 'resource';
        this.resourceId = options.resourceId;
        this.boardResourceId = options.boardResourceId;
        this.groupId = options.groupId;
        this.resourceData = resourceData;
        this.width = cardWidth;
        this.height = cardHeight;
        
        // Disable rotation completely (same as business groups)
        this.lockRotation = true;
        this.hasRotate = false;
        this.setControlVisible('mtr', false);
    },
    
    toObject: function() {
        return fabric.util.object.extend(this.callSuper('toObject'), {
            objectType: this.objectType,
            resourceId: this.resourceId,
            boardResourceId: this.boardResourceId,
            groupId: this.groupId,
            type: 'resourceCard'
        });
    }
});

fabric.ResourceCard.fromObject = function(object, callback) {
    // During deserialization, we need to reconstruct the ResourceCard
    fabric.Group.fromObject(object, function(group) {
        // Convert back to ResourceCard and restore all properties
        group.type = 'resourceCard';
        group.objectType = 'resource';
        group.resourceId = object.resourceId;
        group.boardResourceId = object.boardResourceId;
        group.groupId = object.groupId;
        
        // Disable rotation completely (must be set after deserialization)
        group.lockRotation = true;
        group.hasRotate = false;
        group.setControlVisible('mtr', false);
        
        // Disable other controls
        group.hasControls = false;
        group.hasBorders = true;
        
        callback && callback(group);
    });
};

/**
 * Handle API response errors (401, 403, etc.)
 */
function handleApiError(response, data) {
    if (response.status === 401) {
        // Session expired - redirect to login
        alert('Ваша сессия истекла. Пожалуйста, войдите снова.');
        window.location.href = '/login';
        return true;
    }
    return false;
}

// Global state
let currentBoard = null;
let fabricCanvas = null;
let allResources = [];
let currentFilter = 'all';
let autoSaveTimer = null;

// Undo/Redo state
let undoStack = [];
let redoStack = [];
let maxUndoSteps = 50;
let isRestoring = false; // Flag to prevent saving during restoration
let isCreatingObjects = false; // Flag to prevent saving during object creation

// Grid state
let gridVisible = false;
let gridSize = 50; // Grid cell size in pixels

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeBusinessContext();
});

/**
 * Main initialization function
 */
async function initializeBusinessContext() {
    setupEventListeners();
    
    // Check if we should restore a previously opened board
    const lastBoardId = localStorage.getItem('business_context_last_board');
    
    if (lastBoardId && lastBoardId !== 'list') {
        // Validate board exists before trying to open it
        try {
            const response = await fetch(`/api/business-context/boards/${parseInt(lastBoardId)}`);
            const data = await response.json();
            if (data.success) {
                // Board exists, open it
                openBoard(parseInt(lastBoardId));
            } else {
                // Board doesn't exist (e.g., after re-seed) - show list silently
                localStorage.setItem('business_context_last_board', 'list');
                loadBoards();
            }
        } catch (error) {
            // Error fetching board - show list silently
            localStorage.setItem('business_context_last_board', 'list');
            loadBoards();
        }
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
    
    // Create board form submit handler
    const createBoardForm = document.getElementById('createBoardForm');
    if (createBoardForm) {
        createBoardForm.addEventListener('submit', function(e) {
            e.preventDefault();
            createBoard();
        });
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
    
    // Grid toggle
    document.getElementById('gridToggleBtn')?.addEventListener('click', toggleGrid);
    
    // Undo/Redo controls
    document.getElementById('undoBtn')?.addEventListener('click', undo);
    document.getElementById('redoBtn')?.addEventListener('click', redo);
    
    // Toolbox toggle
    document.getElementById('toggleToolboxBtn')?.addEventListener('click', toggleToolbox);
    
    // Save board button
    // Manual save button removed - autosave only
    
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
    
    // Click to create at default position (deprecated, but keep for compatibility)
    groupTool.addEventListener('click', function(e) {
        // Only trigger on direct click, not when starting drag
        if (!e.defaultPrevented) {
            createGroupOnCanvas();
        }
    });
    
    // Drag to create at specific position
    groupTool.addEventListener('dragstart', function(e) {
        e.dataTransfer.setData('tool', 'group');
        e.dataTransfer.effectAllowed = 'copy';
        this.classList.add('dragging');
    });
    
    groupTool.addEventListener('dragend', function() {
        this.classList.remove('dragging');
    });
    
    // Prevent default context menu on right-click
    groupTool.addEventListener('contextmenu', function(e) {
        e.preventDefault();
    });
}

/**
 * Setup free objects tools (text, rectangle)
 */
function setupFreeObjectsTools() {
    // Text tool
    const textTool = document.querySelector('[data-tool="text"]');
    if (textTool) {
        textTool.addEventListener('click', function(e) {
            if (!e.defaultPrevented) {
                createTextOnCanvas();
            }
        });
        
        textTool.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('tool', 'text');
            e.dataTransfer.effectAllowed = 'copy';
            this.classList.add('dragging');
        });
        
        textTool.addEventListener('dragend', function() {
            this.classList.remove('dragging');
        });
        
        // Prevent default context menu on right-click
        textTool.addEventListener('contextmenu', function(e) {
            e.preventDefault();
        });
    }
    
    // Rectangle tool
    const rectangleTool = document.querySelector('[data-tool="rectangle"]');
    if (rectangleTool) {
        rectangleTool.addEventListener('click', function(e) {
            if (!e.defaultPrevented) {
                createRectangleOnCanvas();
            }
        });
        
        rectangleTool.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('tool', 'rectangle');
            e.dataTransfer.effectAllowed = 'copy';
            this.classList.add('dragging');
        });
        
        rectangleTool.addEventListener('dragend', function() {
            this.classList.remove('dragging');
        });
        
        // Prevent default context menu on right-click
        rectangleTool.addEventListener('contextmenu', function(e) {
            e.preventDefault();
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
    
    // Group properties - color buttons
    document.querySelectorAll('.color-option').forEach(button => {
        button.addEventListener('click', function() {
            const activeObj = fabricCanvas.getActiveObject();
            if (activeObj && activeObj.objectType === 'group') {
                const newColor = this.dataset.color;
                activeObj.groupColor = newColor;
                
                // Update the background rectangle child (children[0])
                const children = activeObj.getObjects();
                const groupRect = children[0];
                if (groupRect) {
                    groupRect.set({
                        stroke: newColor,
                        fill: hexToRgba(newColor, 0.05)
                    });
                }
                
                // Update active state on buttons
                document.querySelectorAll('.color-option').forEach(btn => {
                    btn.classList.remove('active');
                });
                this.classList.add('active');
                
                fabricCanvas.renderAll();
                
                // Update in database
                updateGroupInDatabase(activeObj);
                scheduleAutoSave();
            }
        });
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
        if (activeObj && activeObj.objectType === 'freeText') {
            fabricCanvas.remove(activeObj);
            fabricCanvas.renderAll();
            hidePropertiesPanel();
            scheduleAutoSave();
        } else if (activeObj && activeObj.objectType === 'freeRect') {
            fabricCanvas.remove(activeObj);
            fabricCanvas.renderAll();
            hidePropertiesPanel();
            scheduleAutoSave();
        } else if (activeObj && activeObj.objectType === 'group') {
            // Groups need database deletion
            deleteGroup(activeObj);
            hidePropertiesPanel();
        }
    });
}

/**
 * Show properties panel for selected object
 */
function showPropertiesPanel(obj) {
    if (!obj || (obj.objectType !== 'freeText' && obj.objectType !== 'freeRect' && obj.objectType !== 'group')) {
        hidePropertiesPanel();
        return;
    }
    
    const propertiesPanel = document.getElementById('propertiesPanel');
    const textProperties = document.getElementById('textProperties');
    const rectangleProperties = document.getElementById('rectangleProperties');
    const groupProperties = document.getElementById('groupProperties');
    const layerButtons = document.getElementById('bringToFrontBtn')?.parentElement.parentElement;
    
    // Hide all property sections
    textProperties.style.display = 'none';
    rectangleProperties.style.display = 'none';
    groupProperties.style.display = 'none';
    
    // Show relevant properties
    if (obj.objectType === 'freeText') {
        textProperties.style.display = 'block';
        
        // Update controls to match object
        document.getElementById('fontSize').value = obj.fontSize || 24;
        document.getElementById('textColor').value = obj.fill || '#1F2937';
        document.getElementById('boldBtn').classList.toggle('active', obj.fontWeight === 'bold');
        document.getElementById('italicBtn').classList.toggle('active', obj.fontStyle === 'italic');
        document.getElementById('underlineBtn').classList.toggle('active', obj.underline === true);
        
        // Show layer buttons for free objects
        if (layerButtons) layerButtons.style.display = 'block';
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
        
        // Show layer buttons for free objects
        if (layerButtons) layerButtons.style.display = 'block';
    } else if (obj.objectType === 'group') {
        groupProperties.style.display = 'block';
        
        // Highlight the active color
        const currentColor = obj.groupColor || '#92400E';
        document.querySelectorAll('.color-option').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.color === currentColor);
        });
        
        // Hide layer buttons for groups (they're always at the bottom)
        if (layerButtons) layerButtons.style.display = 'none';
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
            // Allow copying groups and free objects (not resources - they're tied to DB)
            if (activeObj && (activeObj.objectType === 'group' || activeObj.objectType === 'freeText' || activeObj.objectType === 'freeRect')) {
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
            if (activeObj) {
                // Don't delete if we're editing text
                if (activeObj.objectType === 'freeText' && activeObj.isEditing) {
                    return;
                }
                
                e.preventDefault();
                
                if (activeObj.objectType === 'group') {
                    deleteGroup(activeObj);
                } else if (activeObj.objectType === 'resource') {
                    deleteResourceFromBoard(activeObj);
                } else if (activeObj.objectType === 'freeText' || activeObj.objectType === 'freeRect') {
                    fabricCanvas.remove(activeObj);
                    fabricCanvas.renderAll();
                    hidePropertiesPanel();
                    scheduleAutoSave();
                }
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
        
        // Deselect: Esc key
        if (e.key === 'Escape') {
            if (fabricCanvas) {
                fabricCanvas.discardActiveObject();
                fabricCanvas.renderAll();
                hidePropertiesPanel();
            }
        }
        
        // Select All: Ctrl+A
        if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
            if (fabricCanvas) {
                e.preventDefault();
                const allObjects = fabricCanvas.getObjects().filter(obj => 
                    obj.selectable && 
                    (obj.objectType === 'group' || obj.objectType === 'resource' || 
                     obj.objectType === 'freeText' || obj.objectType === 'freeRect')
                );
                
                // Also include group children (labels and cost badges) in the selection
                // With fabric.Group, children are already part of the group object
                // No need to manually add groupText and groupCost
                if (allObjects.length > 0) {
                    const selection = new fabric.ActiveSelection(allObjects, {
                        canvas: fabricCanvas
                    });
                    fabricCanvas.setActiveObject(selection);
                    fabricCanvas.renderAll();
                }
            }
        }
        
        // Zoom In: Ctrl+= or Ctrl++
        if ((e.ctrlKey || e.metaKey) && (e.key === '=' || e.key === '+')) {
            e.preventDefault();
            zoomIn();
        }
        
        // Zoom Out: Ctrl+-
        if ((e.ctrlKey || e.metaKey) && e.key === '-') {
            e.preventDefault();
            zoomOut();
        }
        
        // Reset Zoom: Ctrl+0
        if ((e.ctrlKey || e.metaKey) && e.key === '0') {
            e.preventDefault();
            zoomReset();
        }
        
        // Undo: Ctrl+Z
        if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            undo();
        }
        
        // Redo: Ctrl+Shift+Z or Ctrl+Y
        if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
            e.preventDefault();
            redo();
        }
    });
}

/**
 * Save current canvas state to undo stack
 */
function saveToUndoStack() {
    if (!fabricCanvas) {
        return;
    }
    
    // Don't save during restoration
    if (isRestoring) {
        return;
    }
    
    // Don't save during object creation (prevents intermediate states from overwriting the "before" state)
    if (isCreatingObjects) {
        return;
    }
    
    // Get current canvas state (excluding grid lines)
    const canvasJSON = fabricCanvas.toJSON(['objectType', 'fabricId', 'groupName', 'groupColor', 'calculatedCost', 'dbId', 'parentFabricId', 'resourceId', 'boardResourceId', 'groupId']);
    
    // Filter out grid lines - they should never be saved
    const filteredObjects = canvasJSON.objects.filter(obj => obj.objectType !== 'gridLine');
    
    const state = {
        objects: {
            ...canvasJSON,
            objects: filteredObjects
        },
        viewport: {
            zoom: fabricCanvas.getZoom(),
            pan: fabricCanvas.viewportTransform.slice()
        },
        timestamp: Date.now()
    };
    
    console.log('💾 SAVE TO UNDO STACK:', {
        totalObjects: filteredObjects.length,
        resources: filteredObjects.filter(o => o.objectType === 'resource').length,
        groups: filteredObjects.filter(o => o.objectType === 'group').length,
        resourceDetails: filteredObjects.filter(o => o.objectType === 'resource').map(r => ({
            resourceId: r.resourceId,
            boardResourceId: r.boardResourceId,
            left: r.left,
            top: r.top
        }))
    });
    
    // Add to undo stack
    undoStack.push(state);
    
    // Limit stack size
    if (undoStack.length > maxUndoSteps) {
        undoStack.shift();
    }
    
    // Clear redo stack when new action is performed
    redoStack = [];
    
    // Update button states
    updateUndoRedoButtons();
}

/**
 * Undo last action
 */
function undo() {
    if (undoStack.length === 0) {
        return;
    }
    
    console.log('⏪ UNDO TRIGGERED');
    
    // Save current state to redo stack (excluding grid lines)
    const canvasJSON = fabricCanvas.toJSON(['objectType', 'fabricId', 'groupName', 'groupColor', 'calculatedCost', 'dbId', 'parentFabricId', 'resourceId', 'boardResourceId', 'groupId']);
    const filteredObjects = canvasJSON.objects.filter(obj => obj.objectType !== 'gridLine');
    
    console.log('📸 Current state before undo:', {
        totalObjects: filteredObjects.length,
        resources: filteredObjects.filter(o => o.objectType === 'resource').length,
        resourceDetails: filteredObjects.filter(o => o.objectType === 'resource').map(r => ({
            resourceId: r.resourceId,
            boardResourceId: r.boardResourceId,
            left: r.left,
            top: r.top
        }))
    });
    
    const currentState = {
        objects: {
            ...canvasJSON,
            objects: filteredObjects
        },
        viewport: {
            zoom: fabricCanvas.getZoom(),
            pan: fabricCanvas.viewportTransform.slice()
        },
        timestamp: Date.now()
    };
    redoStack.push(currentState);
    
    // Restore previous state
    const previousState = undoStack.pop();
    
    console.log('🔙 Restoring to previous state:', {
        totalObjects: previousState.objects.objects.length,
        resources: previousState.objects.objects.filter(o => o.objectType === 'resource').length,
        resourceDetails: previousState.objects.objects.filter(o => o.objectType === 'resource').map(r => ({
            resourceId: r.resourceId,
            boardResourceId: r.boardResourceId,
            left: r.left,
            top: r.top
        }))
    });
    
    restoreCanvasState(previousState);
    
    // Update button states
    updateUndoRedoButtons();
}

/**
 * Redo last undone action
 */
function redo() {
    if (redoStack.length === 0) return;
    
    // Save current state to undo stack (excluding grid lines)
    const canvasJSON = fabricCanvas.toJSON(['objectType', 'fabricId', 'groupName', 'groupColor', 'calculatedCost', 'dbId', 'parentFabricId', 'resourceId', 'boardResourceId', 'groupId']);
    const filteredObjects = canvasJSON.objects.filter(obj => obj.objectType !== 'gridLine');
    
    const currentState = {
        objects: {
            ...canvasJSON,
            objects: filteredObjects
        },
        viewport: {
            zoom: fabricCanvas.getZoom(),
            pan: fabricCanvas.viewportTransform.slice()
        },
        timestamp: Date.now()
    };
    undoStack.push(currentState);
    
    // Restore next state
    const nextState = redoStack.pop();
    restoreCanvasState(nextState);
    
    // Update button states
    updateUndoRedoButtons();
}

/**
 * Restore canvas to a saved state
 */
function restoreCanvasState(state) {
    if (!fabricCanvas || !state) {
        console.log('❌ Cannot restore: no canvas or state');
        return;
    }
    
    console.log('🔄 RESTORE CANVAS STATE:', {
        objectsToRestore: state.objects.objects.length,
        resources: state.objects.objects.filter(o => o.objectType === 'resource').length,
        resourceDetails: state.objects.objects.filter(o => o.objectType === 'resource').map(r => ({
            resourceId: r.resourceId,
            boardResourceId: r.boardResourceId,
            left: r.left,
            top: r.top
        }))
    });
    
    // Set flag to prevent saving during restoration
    isRestoring = true;
    
    // Temporarily remove canvas event listeners to prevent pollution
    fabricCanvas.off('mouse:down');
    fabricCanvas.off('object:modified');
    fabricCanvas.off('object:added');
    fabricCanvas.off('object:removed');
    
    // Clear current canvas
    console.log('🗑️ Clearing canvas');
    fabricCanvas.clear();
    
    // Restore objects
    console.log('📦 Loading objects from JSON');
    fabricCanvas.loadFromJSON(state.objects, function() {
        console.log('✅ Objects loaded from JSON:', fabricCanvas.getObjects().length);
        
        // Log all objects that were restored
        fabricCanvas.forEachObject(function(obj) {
            const logData = {
                objectType: obj.objectType,
                fabricType: obj.type,
                resourceId: obj.resourceId,
                boardResourceId: obj.boardResourceId,
                left: obj.left,
                top: obj.top,
                visible: obj.visible,
                opacity: obj.opacity,
                width: obj.width,
                height: obj.height
            };
            
            if (obj.type === 'group' || obj.type === 'resourceCard') {
                const children = obj.getObjects();
                logData.childCount = children.length;
                logData.children = children.map((child, idx) => ({
                    index: idx,
                    type: child.type,
                    visible: child.visible,
                    opacity: child.opacity
                }));
            }
            
            console.log(`   📦 Restored object:`, logData);
        });
        
        // Restore viewport
        fabricCanvas.setZoom(state.viewport.zoom);
        fabricCanvas.viewportTransform = state.viewport.pan.slice();
        
        // Send all groups to the back (groups should always be behind resources)
        fabricCanvas.forEachObject(function(obj) {
            if (obj.objectType === 'group') {
                obj.sendToBack();
            }
        });
        
        // Update object coordinates after viewport restore for hit detection
        fabricCanvas.forEachObject(function(obj) {
            obj.setCoords();
        });
        fabricCanvas.renderAll(); // Ensure hit detection works after viewport restore
        
        // Re-setup event handlers for all objects
        console.log('🔧 Setting up event handlers');
        setupObjectEventHandlers();
        
        // Update clone badges for all resources after restore
        console.log('🏷️ Updating clone badges');
        const resourceIds = new Set();
        fabricCanvas.forEachObject(function(obj) {
            if (obj.objectType === 'resource' && obj.resourceId) {
                resourceIds.add(obj.resourceId);
            }
        });
        console.log(`   Found ${resourceIds.size} unique resources`);
        resourceIds.forEach(resourceId => updateCloneBadges(resourceId));
        
        console.log('✅ RESTORE COMPLETE - Final object count:', fabricCanvas.getObjects().filter(o => o.objectType === 'resource').length, 'resources');
        
        // Re-attach canvas event listeners
        
        // Mouse down on object - save state BEFORE modification
        fabricCanvas.on('mouse:down', function(opt) {
            const target = opt.target;
            if (target && target.selectable) {
                console.log('🖱️ Mouse down on object:', {
                    type: target.objectType,
                    resourceId: target.resourceId,
                    boardResourceId: target.boardResourceId,
                    left: target.left,
                    top: target.top
                });
                saveToUndoStack();
            }
        });
        
        fabricCanvas.on('object:modified', function(e) {
            const obj = e.target;
            
            // If it's an ActiveSelection (multiple objects), update each group in database
            if (obj.type === 'activeSelection') {
                obj.forEachObject(function(selectedObj) {
                    if (selectedObj.objectType === 'group') {
                        updateGroupInDatabase(selectedObj);
                    }
                });
            }
            // If it's a single group, update the database
            else if (obj && obj.objectType === 'group') {
                updateGroupInDatabase(obj);
            }
            
            scheduleAutoSave();
        });
        
        fabricCanvas.on('object:added', function() {
            saveToUndoStack();
            scheduleAutoSave();
        });
        
        fabricCanvas.on('object:removed', function() {
            saveToUndoStack();
            scheduleAutoSave();
        });
        
        // Update zoom display
        updateZoomDisplay();
        
        // Render
        fabricCanvas.renderAll();
        
        // Re-enable saving after restoration is complete
        isRestoring = false;
        
        // Redraw grid if it was visible
        updateGrid();
        
        // Trigger autosave
        scheduleAutoSave();
    });
}

/**
 * Setup event handlers for all objects on canvas
 */
function setupObjectEventHandlers() {
    if (!fabricCanvas) return;
    
    const objects = fabricCanvas.getObjects();
    
    objects.forEach(function(obj) {
        // Setup group event handlers (fabric.Group with children)
        if (obj.objectType === 'group') {
            // Store initial position for collision detection
            if (!obj.lastValidLeft) {
                obj.lastValidLeft = obj.left;
                obj.lastValidTop = obj.top;
                obj.lastValidWidth = obj.width;
                obj.lastValidHeight = obj.height;
            }
            
            // Setup moving event
            obj.on('moving', function() {
                // Check for intersection with other groups
                if (checkGroupIntersection(this, this)) {
                    // Revert to last valid position
                    this.set({
                        left: this.lastValidLeft,
                        top: this.lastValidTop
                    });
                } else {
                    // Store current position as valid
                    this.lastValidLeft = this.left;
                    this.lastValidTop = this.top;
                }
                // Children move automatically with fabric.Group! ✨
            });
            
            // Setup scaling event
            obj.on('scaling', function() {
                const newWidth = this.width * this.scaleX;
                const newHeight = this.height * this.scaleY;
                
                this.set({
                    width: newWidth,
                    height: newHeight,
                    scaleX: 1,
                    scaleY: 1
                });
                
                // Check for intersection
                if (checkGroupIntersection(this, this)) {
                    // Revert to last valid size
                    this.set({
                        width: this.lastValidWidth,
                        height: this.lastValidHeight,
                        scaleX: 1,
                        scaleY: 1
                    });
                } else {
                    // Store current size as valid
                    this.lastValidWidth = this.width;
                    this.lastValidHeight = this.height;
                }
                // Children resize automatically with fabric.Group! ✨
            });
            
            // Setup modified event
            obj.on('modified', async function() {
                await checkAndUpdateResourcesOutsideGroup(this);
                updateGroupInDatabase(this);
            });
            
            // Setup double-click event
            obj.on('mousedblclick', function() {
                editGroupName(this);
            });
        }
        
        // Setup resource event handlers (restored from undo/redo)
        if (obj.objectType === 'resource' || obj.type === 'resourceCard') {
            // Resources are custom fabric.ResourceCard objects
            // Need to re-attach event handlers after deserialization
            
            const children = obj.getObjects();
            if (children && children.length >= 9) {
                const infoIconCircle = children[3];
                const notesIconCircle = children[5];
                
                // Re-attach click handlers to icons
                if (infoIconCircle) {
                    infoIconCircle.on('mousedown', function(e) {
                        e.e.stopPropagation();
                        showResourceInfo(obj.resourceId);
                    });
                }
                
                if (notesIconCircle) {
                    notesIconCircle.on('mousedown', function(e) {
                        e.e.stopPropagation();
                        showResourceNotes(obj.resourceId);
                    });
                }
            }
            
            // Re-attach modified handler
            obj.on('modified', function() {
                checkResourceGroupAssignment(this);
                updateResourcePosition(this);
            });
            
            obj.setCoords();
        }
    });
}

/**
 * Update undo/redo button states
 */
function updateUndoRedoButtons() {
    const undoBtn = document.getElementById('undoBtn');
    const redoBtn = document.getElementById('redoBtn');
    
    if (undoBtn) {
        undoBtn.disabled = undoStack.length === 0;
    }
    
    if (redoBtn) {
        redoBtn.disabled = redoStack.length === 0;
    }
}

/**
 * Paste (duplicate) an object
 */
function pasteObject(obj) {
    if (!fabricCanvas || !obj) return;
    
    // Save state BEFORE pasting (so undo can restore to this state)
    saveToUndoStack();
    
    // Set flag to prevent intermediate saves during object creation
    isCreatingObjects = true;
    
    // Handle groups separately (they need DB creation)
    if (obj.objectType === 'group') {
        pasteGroup(obj);
        return;
    }
    
    // Handle free objects (text, rectangles)
    obj.clone(function(cloned) {
        cloned.set({
            left: cloned.left + 20,
            top: cloned.top + 20,
            // Explicitly preserve custom properties
            objectType: obj.objectType
        });
        
        // Set up toObject method for the cloned object
        if (obj.objectType === 'freeText') {
            cloned.toObject = (function(toObject) {
                return function() {
                    return fabric.util.object.extend(toObject.call(this), {
                        objectType: this.objectType
                    });
                };
            })(fabric.Text.prototype.toObject);
        } else if (obj.objectType === 'freeRect') {
            cloned.toObject = (function(toObject) {
                return function() {
                    return fabric.util.object.extend(toObject.call(this), {
                        objectType: this.objectType
                    });
                };
            })(fabric.Rect.prototype.toObject);
        }
        
        fabricCanvas.add(cloned);
        fabricCanvas.setActiveObject(cloned);
        fabricCanvas.renderAll();
        
        // Re-enable automatic saves
        isCreatingObjects = false;
        
        scheduleAutoSave();
    });
}

/**
 * Paste a group (clone with DB creation)
 */
async function pasteGroup(originalGroup) {
    if (!fabricCanvas || !currentBoard) return;
    
    const newFabricId = 'group_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // Initial position offset from original
    let initialLeft = originalGroup.left + 30;
    let initialTop = originalGroup.top + 30;
    
    // Find a non-overlapping position
    const adjustedPosition = findNonOverlappingPosition(
        initialLeft, 
        initialTop, 
        originalGroup.width, 
        originalGroup.height
    );
    
    try {
        // Create group in database with adjusted position
        const response = await fetch(`/api/business-context/boards/${currentBoard.id}/groups`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: originalGroup.groupName + ' (Copy)',
                fabric_id: newFabricId,
                position_x: adjustedPosition.left,
                position_y: adjustedPosition.top,
                width: originalGroup.width,
                height: originalGroup.height,
                color: originalGroup.groupColor || '#3B82F6',
                calculated_cost: 0
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Clone the group (clones all children automatically!)
            originalGroup.clone(function(clonedGroup) {
                clonedGroup.set({
                    left: adjustedPosition.left,
                    top: adjustedPosition.top,
                    fabricId: newFabricId,
                    groupName: originalGroup.groupName + ' (Copy)',
                    groupColor: originalGroup.groupColor || '#3B82F6',
                    calculatedCost: 0,
                    dbId: data.group.id,
                    objectType: 'group',
                    lockRotation: true,
                    hasRotate: false
                });
                
                // Disable rotation control
                clonedGroup.setControlVisible('mtr', false);
                
                // Update the name in the cloned text child
                const children = clonedGroup.getObjects();
                const groupText = children[1];
                if (groupText) {
                    groupText.set('text', originalGroup.groupName + ' (Copy)');
                }
                
                // Preserve toObject method
                clonedGroup.toObject = (function(toObject) {
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
                })(fabric.Group.prototype.toObject);
                
                fabricCanvas.add(clonedGroup);
                
                // Store initial position for collision detection
                clonedGroup.lastValidLeft = clonedGroup.left;
                clonedGroup.lastValidTop = clonedGroup.top;
                clonedGroup.lastValidWidth = clonedGroup.width;
                clonedGroup.lastValidHeight = clonedGroup.height;
                
                // Setup event handlers
                clonedGroup.on('moving', function() {
                    // Check for intersection with other groups
                    if (checkGroupIntersection(this, this)) {
                        // Revert to last valid position
                        this.set({
                            left: this.lastValidLeft,
                            top: this.lastValidTop
                        });
                    } else {
                        // Store current position as valid
                        this.lastValidLeft = this.left;
                        this.lastValidTop = this.top;
                    }
                    // Children move automatically! ✨
                });
                
                clonedGroup.on('scaling', function() {
                    const newWidth = this.width * this.scaleX;
                    const newHeight = this.height * this.scaleY;
                    
                    // Temporarily apply new size to check for intersection
                    this.set({
                        width: newWidth,
                        height: newHeight,
                        scaleX: 1,
                        scaleY: 1
                    });
                    
                    // Check for intersection
                    if (checkGroupIntersection(this, this)) {
                        // Revert to last valid size
                        this.set({
                            width: this.lastValidWidth,
                            height: this.lastValidHeight,
                            scaleX: 1,
                            scaleY: 1
                        });
                    } else {
                        // Store current size as valid
                        this.lastValidWidth = this.width;
                        this.lastValidHeight = this.height;
                    }
                    // Children resize automatically! ✨
                });
                
                // When group movement/resize finishes, check if resources moved outside
                clonedGroup.on('modified', async function() {
                    await checkAndUpdateResourcesOutsideGroup(this);
                    updateGroupInDatabase(this);
                });
                
                clonedGroup.on('mousedblclick', function() {
                    editGroupName(this);
                });
                
                fabricCanvas.setActiveObject(clonedGroup);
                fabricCanvas.renderAll();
                
                // Re-enable automatic saves
                isCreatingObjects = false;
                
                scheduleAutoSave();
            });
        } else {
            isCreatingObjects = false;
            showFlashMessage('error', data.error || 'Failed to copy group');
        }
    } catch (error) {
        isCreatingObjects = false;
        console.error('Error copying group:', error);
        showFlashMessage('error', 'Failed to copy group');
    }
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
            // Board not found (likely after re-seed) - silently go back to list
            localStorage.setItem('business_context_last_board', 'list');
            loadBoards();
            // Don't show error - board not found is expected after re-seed
        }
    } catch (error) {
        console.error('Error opening board:', error);
        // Network error - show error only for unexpected failures
        localStorage.setItem('business_context_last_board', 'list');
        loadBoards();
        // Only show error for actual network failures, not 404s
        if (!error.message?.includes('404')) {
            showFlashMessage('error', 'Ошибка загрузки доски');
        }
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
        
        // Initialize undo/redo buttons
        updateUndoRedoButtons();
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
        height: initialHeight,
        // Make selection more visible
        selectionBorderColor: '#F59E0B',
        selectionLineWidth: 3,
        selectionColor: 'rgba(245, 158, 11, 0.1)'
    });
    
    // Set global selection styling for all objects
    fabric.Object.prototype.set({
        borderColor: '#F59E0B',
        cornerColor: '#F59E0B',
        cornerSize: 10,
        transparentCorners: false,
        borderScaleFactor: 3
    });
    
    // Load canvas state if exists (for free objects only)
    if (currentBoard.canvas_state) {
        try {
            fabricCanvas.loadFromJSON(currentBoard.canvas_state, function() {
                // Remove group and resource objects from canvas_state (they'll be loaded from database)
                const objectsToRemove = [];
                fabricCanvas.getObjects().forEach(obj => {
                    // Groups and resources are now fabric.Group objects
                    // Remove them (their children are automatically removed)
                    if (obj.objectType === 'group' || obj.objectType === 'resource') {
                        objectsToRemove.push(obj);
                    }
                });
                objectsToRemove.forEach(obj => fabricCanvas.remove(obj));
                
                // Now load groups from database (after clearing old ones from canvas_state)
                if (currentBoard.groups && currentBoard.groups.length > 0) {
                    loadGroupsOnCanvas(currentBoard.groups);
                }
                
                // Load placed resources from database
                if (currentBoard.resources && currentBoard.resources.length > 0) {
                    loadResourcesOnCanvas(currentBoard.resources);
                }
                
                fabricCanvas.renderAll();
            });
        } catch (error) {
            console.error('Error loading canvas state:', error);
        }
    } else {
        // No canvas state, just load groups and resources
        if (currentBoard.groups && currentBoard.groups.length > 0) {
            loadGroupsOnCanvas(currentBoard.groups);
        }
        
        if (currentBoard.resources && currentBoard.resources.length > 0) {
            loadResourcesOnCanvas(currentBoard.resources);
        }
    }
    
    // Restore viewport
    if (currentBoard.viewport) {
        const viewport = currentBoard.viewport;
        fabricCanvas.setZoom(viewport.zoom || 1.0);
        fabricCanvas.absolutePan({ x: viewport.pan_x || 0, y: viewport.pan_y || 0 });
        
        // Update object coordinates after viewport restore for hit detection
        fabricCanvas.forEachObject(function(obj) {
            obj.setCoords();
        });
        fabricCanvas.renderAll(); // Ensure hit detection works after viewport restore
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
            updateGrid();
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
            updateGrid();
            scheduleAutoSave();
        }
        
        evt.preventDefault();
        evt.stopPropagation();
    });
    
    // Debounced handler to update coordinates after wheel panning stops
    let wheelPanTimeout;
    const canvasElement = fabricCanvas.wrapperEl;
    canvasElement.addEventListener('wheel', function() {
        clearTimeout(wheelPanTimeout);
        wheelPanTimeout = setTimeout(function() {
            // Update object coordinates after wheel panning stops
            fabricCanvas.forEachObject(function(obj) {
                obj.setCoords();
            });
            fabricCanvas.renderAll();
        }, 150); // Wait 150ms after last wheel event
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
            
            updateGrid();
            scheduleAutoSave();
        }
    });
    
    fabricCanvas.on('mouse:up', function() {
        if (isPanning) {
            isPanning = false;
            fabricCanvas.selection = true;
            fabricCanvas.defaultCursor = spacePressed ? 'grab' : 'default';
            
            // Update all object coordinates after panning to fix hit detection
            // This is required because viewportTransform changes affect hit detection
            fabricCanvas.forEachObject(function(obj) {
                obj.setCoords();
            });
            
            // Force re-render after panning to refresh hit detection
            fabricCanvas.renderAll();
            updateGrid();
        }
    });
    
    // Mouse down on object - save state BEFORE modification
    fabricCanvas.on('mouse:down', function(opt) {
        const target = opt.target;
        if (target && target.selectable) {
            // Save state before any modification starts
            saveToUndoStack();
        }
    });
    
    // Object modified - update database and trigger autosave
    fabricCanvas.on('object:modified', function(e) {
        const obj = e.target;
        
        // If it's an ActiveSelection (multiple objects), update each group in database
        if (obj.type === 'activeSelection') {
            obj.forEachObject(function(selectedObj) {
                if (selectedObj.objectType === 'group') {
                    updateGroupInDatabase(selectedObj);
                }
            });
        }
        // If it's a single group, update the database
        else if (obj && obj.objectType === 'group') {
            updateGroupInDatabase(obj);
        }
        
        scheduleAutoSave();
    });
    
    fabricCanvas.on('object:added', function(opt) {
        saveToUndoStack();
        scheduleAutoSave();
    });
    
    fabricCanvas.on('object:removed', function() {
        saveToUndoStack();
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
        
        // Show menu for groups, text, rectangles, and resources
        if (target && (target.objectType === 'group' || target.objectType === 'freeText' || target.objectType === 'freeRect' || target.objectType === 'resource')) {
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
                    editGroupName(contextTarget);
                    break;
                
                case 'properties':
                    // Show properties panel for free objects and groups
                    showPropertiesPanel(contextTarget);
                    fabricCanvas.setActiveObject(contextTarget);
                    fabricCanvas.renderAll();
                    break;
                
                case 'view-info':
                    // Show resource info modal
                    if (contextTarget.resourceId) {
                        showResourceInfo(contextTarget.resourceId);
                    }
                    break;
                
                case 'edit-notes':
                    // Show resource notes modal
                    if (contextTarget.resourceId) {
                        showResourceNotes(contextTarget.resourceId);
                    }
                    break;
                
                case 'clone':
                    // Clone resource
                    if (contextTarget.objectType === 'resource') {
                        cloneResource(contextTarget);
                    }
                    break;
                    
                case 'delete':
                    if (contextTarget.objectType === 'group') {
                        deleteGroup(contextTarget);
                    } else if (contextTarget.objectType === 'resource') {
                        deleteResourceFromBoard(contextTarget);
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
    // Update object coordinates after zoom for hit detection
    fabricCanvas.forEachObject(function(obj) {
        obj.setCoords();
    });
    fabricCanvas.renderAll();
    updateZoomDisplay();
    updateGrid();
    scheduleAutoSave();
}

function zoomOut() {
    if (!fabricCanvas) return;
    let zoom = fabricCanvas.getZoom();
    zoom = Math.max(zoom * 0.9, 0.1);
    fabricCanvas.setZoom(zoom);
    // Update object coordinates after zoom for hit detection
    fabricCanvas.forEachObject(function(obj) {
        obj.setCoords();
    });
    fabricCanvas.renderAll();
    updateZoomDisplay();
    updateGrid();
    scheduleAutoSave();
}

function zoomReset() {
    if (!fabricCanvas) return;
    fabricCanvas.setZoom(1);
    fabricCanvas.absolutePan({ x: 0, y: 0 });
    // Update object coordinates after zoom/pan reset for hit detection
    fabricCanvas.forEachObject(function(obj) {
        obj.setCoords();
    });
    fabricCanvas.renderAll();
    updateZoomDisplay();
    updateGrid();
    scheduleAutoSave();
}

function updateZoomDisplay() {
    if (!fabricCanvas) return;
    const zoom = Math.round(fabricCanvas.getZoom() * 100);
    document.getElementById('zoomLevel').textContent = zoom + '%';
}

/**
 * Toggle grid visibility
 */
function toggleGrid() {
    gridVisible = !gridVisible;
    
    const gridBtn = document.getElementById('gridToggleBtn');
    if (gridVisible) {
        gridBtn.classList.add('active');
        drawGrid();
    } else {
        gridBtn.classList.remove('active');
        clearGrid();
    }
}

/**
 * Draw grid on canvas
 */
function drawGrid() {
    if (!fabricCanvas || !gridVisible) return;
    
    // Remove existing grid lines
    clearGrid();
    
    const zoom = fabricCanvas.getZoom();
    const vpt = fabricCanvas.viewportTransform;
    const width = fabricCanvas.width / zoom;
    const height = fabricCanvas.height / zoom;
    
    // Calculate grid offset based on viewport
    const offsetX = -vpt[4] / zoom;
    const offsetY = -vpt[5] / zoom;
    
    // Adjust grid start to align with grid size
    const startX = Math.floor(offsetX / gridSize) * gridSize;
    const startY = Math.floor(offsetY / gridSize) * gridSize;
    
    const endX = offsetX + width;
    const endY = offsetY + height;
    
    const gridLines = [];
    
    // Temporarily set flag to prevent saving grid lines to undo
    isRestoring = true;
    
    // Vertical lines
    for (let x = startX; x <= endX; x += gridSize) {
        const line = new fabric.Line([x, offsetY, x, offsetY + height], {
            stroke: '#E5E7EB',
            strokeWidth: 1 / zoom,
            selectable: false,
            evented: false,
            objectType: 'gridLine'
        });
        gridLines.push(line);
        fabricCanvas.add(line);
    }
    
    // Horizontal lines
    for (let y = startY; y <= endY; y += gridSize) {
        const line = new fabric.Line([offsetX, y, offsetX + width, y], {
            stroke: '#E5E7EB',
            strokeWidth: 1 / zoom,
            selectable: false,
            evented: false,
            objectType: 'gridLine'
        });
        gridLines.push(line);
        fabricCanvas.add(line);
    }
    
    // Re-enable saving
    isRestoring = false;
    
    // Send grid lines to back
    gridLines.forEach(line => fabricCanvas.sendToBack(line));
    
    fabricCanvas.renderAll();
}

/**
 * Clear grid from canvas
 */
function clearGrid() {
    if (!fabricCanvas) return;
    
    // Temporarily set flag to prevent saving when removing grid lines
    isRestoring = true;
    
    const objects = fabricCanvas.getObjects();
    const gridLines = objects.filter(obj => obj.objectType === 'gridLine');
    
    gridLines.forEach(line => fabricCanvas.remove(line));
    
    // Re-enable saving
    isRestoring = false;
    
    fabricCanvas.renderAll();
}

/**
 * Update grid on zoom or pan
 */
function updateGrid() {
    if (gridVisible) {
        drawGrid();
    }
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
        // Pass current board ID to get board-specific placement status
        const url = currentBoard 
            ? `/api/business-context/available-resources?board_id=${currentBoard.id}`
            : '/api/business-context/available-resources';
        
        const response = await fetch(url);
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
                        ${resource.daily_cost ? `<div class="resource-cost">${(resource.daily_cost * 30).toFixed(2)} ₽/мес</div>` : ''}
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
    const resourceItems = document.querySelectorAll('.resource-item');
    
    resourceItems.forEach(item => {
        const isPlaced = item.classList.contains('placed');
        
        // Only add drag handlers to unplaced resources
        if (!isPlaced) {
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
        }
        
        // Add right-click context menu to ALL resources (placed and unplaced)
        item.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            const resourceId = parseInt(this.dataset.resourceId);
            const isResourcePlaced = this.classList.contains('placed');
            showResourceContextMenu(e, resourceId, isResourcePlaced);
        });
    });
}

/**
 * Show resource context menu
 */
function showResourceContextMenu(e, resourceId, isPlaced) {
    const contextMenu = document.getElementById('resourceContextMenu');
    if (!contextMenu) return;
    
    // Position the menu
    contextMenu.style.left = e.pageX + 'px';
    contextMenu.style.top = e.pageY + 'px';
    contextMenu.style.display = 'block';
    
    // Store resource ID for action handlers
    contextMenu.dataset.resourceId = resourceId;
    
    // Remove existing event listeners by cloning
    const newMenu = contextMenu.cloneNode(true);
    contextMenu.parentNode.replaceChild(newMenu, contextMenu);
    
    // Hide/show Show and Place options based on whether resource is already placed
    const showOption = newMenu.querySelector('[data-action="show"]');
    const placeOption = newMenu.querySelector('[data-action="place"]');
    const separator = placeOption ? placeOption.previousElementSibling : null;
    
    if (isPlaced) {
        // Resource already placed - show Show option, hide Place option and separator
        if (showOption) showOption.style.display = 'flex';
        if (placeOption) placeOption.style.display = 'none';
        if (separator && separator.classList.contains('context-menu-separator')) {
            separator.style.display = 'none';
        }
    } else {
        // Resource not placed - hide Show option, show Place option and separator
        if (showOption) showOption.style.display = 'none';
        if (placeOption) placeOption.style.display = 'flex';
        if (separator && separator.classList.contains('context-menu-separator')) {
            separator.style.display = 'block';
        }
    }
    
    // Add event listeners to menu items
    newMenu.querySelectorAll('.context-menu-item').forEach(item => {
        item.addEventListener('click', function() {
            const action = this.dataset.action;
            handleResourceContextAction(action, resourceId);
            hideResourceContextMenu();
        });
    });
}

/**
 * Hide resource context menu
 */
function hideResourceContextMenu() {
    const contextMenu = document.getElementById('resourceContextMenu');
    if (contextMenu) {
        contextMenu.style.display = 'none';
    }
}

/**
 * Show resource on canvas - bring it into view and select it
 * If resource is already centered and selected, cycle to next clone
 */
function showResourceOnCanvas(resourceId) {
    if (!fabricCanvas || !currentBoard) {
        showFlashMessage('error', 'Откройте доску');
        return;
    }
    
    // Find all instances (clones) of this resource on canvas
    const objects = fabricCanvas.getObjects();
    const resourceInstances = objects.filter(obj => 
        obj.objectType === 'resource' && obj.resourceId === resourceId
    );
    
    if (resourceInstances.length === 0) {
        showFlashMessage('error', 'Ресурс не найден на доске');
        return;
    }
    
    // Check if currently selected object is one of these instances and is already centered
    const activeObj = fabricCanvas.getActiveObject();
    let targetResource = null;
    
    if (activeObj && activeObj.resourceId === resourceId && resourceInstances.length > 1) {
        // Find current instance index
        const currentIndex = resourceInstances.findIndex(obj => obj === activeObj);
        
        // Check if current resource is centered (within 50px of screen center)
        const canvasElement = fabricCanvas.wrapperEl;
        const canvasWidth = canvasElement.offsetWidth;
        const canvasHeight = canvasElement.offsetHeight;
        const zoom = fabricCanvas.getZoom();
        const vpt = fabricCanvas.viewportTransform;
        
        const screenX = activeObj.left * zoom + vpt[4];
        const screenY = activeObj.top * zoom + vpt[5];
        const screenCenterX = canvasWidth / 2;
        const screenCenterY = canvasHeight / 2;
        
        const isCentered = (
            Math.abs(screenX - screenCenterX) < 50 &&
            Math.abs(screenY - screenCenterY) < 50
        );
        
        if (isCentered && currentIndex !== -1) {
            // Cycle to next clone
            const nextIndex = (currentIndex + 1) % resourceInstances.length;
            targetResource = resourceInstances[nextIndex];
        }
    }
    
    // If no cycling needed, use first instance
    if (!targetResource) {
        targetResource = resourceInstances[0];
    }
    
    // Deselect any currently selected objects
    fabricCanvas.discardActiveObject();
    fabricCanvas.renderAll();
    
    // Get resource center in canvas coordinates (not viewport coordinates)
    // targetResource properties (left, top, width, height) are in canvas space
    const centerX = targetResource.left + targetResource.width / 2;
    const centerY = targetResource.top + targetResource.height / 2;
    
    // Get canvas wrapper element dimensions (actual visible area)
    const canvasElement = fabricCanvas.wrapperEl;
    const canvasWidth = canvasElement.offsetWidth;
    const canvasHeight = canvasElement.offsetHeight;
    
    // Get current zoom
    const zoom = fabricCanvas.getZoom();
    
    // Fabric.js viewport transform: screenX = canvasX * zoom + vpt[4]
    // To center: canvasWidth/2 = centerX * zoom + new_vpt[4]
    // Therefore: new_vpt[4] = canvasWidth/2 - centerX * zoom
    const panX = canvasWidth / 2 - centerX * zoom;
    const panY = canvasHeight / 2 - centerY * zoom;
    
    // Pan canvas to center on resource
    fabricCanvas.viewportTransform[4] = panX;
    fabricCanvas.viewportTransform[5] = panY;
    
    // Update object coordinates after panning
    fabricCanvas.forEachObject(function(obj) {
        obj.setCoords();
    });
    
    // Select the target resource
    fabricCanvas.setActiveObject(targetResource);
    fabricCanvas.renderAll();
    
    // Update grid and auto-save
    updateGrid();
    scheduleAutoSave();
}

/**
 * Handle resource context menu actions
 */
function handleResourceContextAction(action, resourceId) {
    switch (action) {
        case 'info':
            // Show resource info modal with resource ID
            showResourceInfo(resourceId);
            break;
            
        case 'notes':
            // Show notes editor for resource
            showResourceNotes(resourceId);
            break;
            
        case 'show':
            // Find resource on canvas and bring it into view, then select it
            showResourceOnCanvas(resourceId);
            break;
            
        case 'place':
            // Place resource in center of visible canvas area
            if (!currentBoard) {
                showFlashMessage('error', 'Откройте доску');
                return;
            }
            
            // Get center of visible canvas area
            const vpt = fabricCanvas.viewportTransform;
            const zoom = fabricCanvas.getZoom();
            const centerX = (fabricCanvas.width / 2 - vpt[4]) / zoom;
            const centerY = (fabricCanvas.height / 2 - vpt[5]) / zoom;
            
            placeResourceOnCanvas(resourceId, centerX, centerY);
            break;
    }
}

// Hide context menu when clicking elsewhere
document.addEventListener('click', function(e) {
    if (!e.target.closest('.context-menu')) {
        hideResourceContextMenu();
    }
});

// Hide context menu on scroll
document.addEventListener('scroll', hideResourceContextMenu, true);

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
        
        // Convert screen coordinates to canvas coordinates
        const pointer = fabricCanvas.getPointer(e);
        console.log('📥 Drop at canvas coords:', pointer);
        
        // Check if it's a resource
        const resourceId = e.dataTransfer.getData('text/plain');
        if (resourceId) {
            await placeResourceOnCanvas(parseInt(resourceId), pointer.x, pointer.y);
            return;
        }
        
        // Check if it's a tool (group, text, rectangle)
        const tool = e.dataTransfer.getData('tool');
        if (tool) {
            switch(tool) {
                case 'group':
                    await createGroupOnCanvas(pointer.x, pointer.y);
                    break;
                case 'text':
                    createTextOnCanvas(pointer.x, pointer.y);
                    break;
                case 'rectangle':
                    createRectangleOnCanvas(pointer.x, pointer.y);
                    break;
            }
        }
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
    
    // Save state BEFORE placing resource (so undo can restore to this state)
    saveToUndoStack();
    
    // Set flag to prevent intermediate saves during object creation
    isCreatingObjects = true;
    
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
        isCreatingObjects = false;
        showFlashMessage('error', 'Ресурс не найден');
        return;
    }
    
    // Note: We allow multiple placements (clones) of the same resource
    // No need to check is_placed - backend handles this now
    
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
            console.log('✅ Resource placed. Group:', groupId || 'none');
            
            // Create Fabric.js object for resource
            createResourceObject(resourceData, x, y, data.board_resource.id, groupId);
            
            // Reload resources to update toolbox (shows placed badge, updates counts)
            await loadResources();
            
            // Update costs for ALL groups containing this resource
            // This ensures cost splitting is recalculated if clones exist in multiple groups
            await updateCostsForAllGroupsWithResource(resourceId);
            
            // Re-enable automatic saves
            isCreatingObjects = false;
            
            scheduleAutoSave();
        } else {
            isCreatingObjects = false;
            showFlashMessage('error', data.error || 'Ошибка размещения ресурса');
        }
    } catch (error) {
        isCreatingObjects = false;
        console.error('Error placing resource:', error);
        showFlashMessage('error', 'Ошибка размещения ресурса');
    }
}

/**
 * Create fabric.ResourceCard object on canvas (custom monolithic class)
 */
function createResourceObject(resourceData, x, y, boardResourceId, groupId, isAbsolutePosition = false) {
    // Calculate final position
    // If isAbsolutePosition is true, x/y are already the final card positions
    // If false (default), x/y are click positions that need to be centered
    const cardLeft = isAbsolutePosition ? x : (x - 60);
    const cardTop = isAbsolutePosition ? y : (y - 40);
    
    // Create the custom ResourceCard object
    const resourceCard = new fabric.ResourceCard(resourceData, {
        left: cardLeft,
        top: cardTop,
        resourceId: resourceData.id,
        boardResourceId: boardResourceId,
        groupId: groupId
    });
    
    // Get child elements for event handling
    const children = resourceCard.getObjects();
    const infoIcon = children[3];  // Info icon circle
    const notesIcon = children[5];  // Notes icon circle
    
    // Add to canvas
    fabricCanvas.add(resourceCard);
    
    console.log('✅ ResourceCard created:', {
        objectType: resourceCard.objectType,
        fabricType: resourceCard.type,
        resourceId: resourceCard.resourceId,
        boardResourceId: resourceCard.boardResourceId,
        childCount: children.length,
        left: resourceCard.left,
        top: resourceCard.top
    });
    
    // Setup event handlers for icon clicks
    if (infoIcon) {
        infoIcon.on('mousedown', function(e) {
            e.e.stopPropagation();
            showResourceInfo(resourceCard.resourceId);
        });
    }
    
    if (notesIcon) {
        notesIcon.on('mousedown', function(e) {
            e.e.stopPropagation();
            showResourceNotes(resourceCard.resourceId);
        });
    }
    
    // Modified event - check group assignment and save position
    resourceCard.on('modified', function() {
        checkResourceGroupAssignment(this);
        updateResourcePosition(this);
    });
    
    // Render
    fabricCanvas.renderAll();
}


/**
 * Get group at specific position (for drop detection)
 */
function getGroupAtPosition(x, y) {
    console.log('🔍 getGroupAtPosition:', { x, y });
    const objects = fabricCanvas.getObjects();
    
    const groups = objects.filter(obj => obj.objectType === 'group');
    
    // Check each group using absolute bounding rect coordinates
    for (const obj of groups) {
        const bounds = obj.getBoundingRect(true); // true = absolute coordinates
        
        // Simple point-in-rectangle check
        if (x >= bounds.left && 
            x <= bounds.left + bounds.width &&
            y >= bounds.top && 
            y <= bounds.top + bounds.height) {
            console.log('   ✅ Found group:', obj.dbId);
            return obj.dbId;
        }
    }
    
    console.log('   ❌ No group found at this position');
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
        
        // Update database and group costs for ALL groups containing this resource
        updateResourceGroupAssignment(resourceObj.boardResourceId, newGroupId, oldGroupId, resourceObj.resourceId);
    }
}

/**
 * Update resource position in database
 */
async function updateResourcePosition(resourceObj) {
    if (!resourceObj.boardResourceId) return;
    
    try {
        await fetch(`/api/business-context/board-resources/${resourceObj.boardResourceId}`, {
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
async function updateResourceGroupAssignment(boardResourceId, newGroupId, oldGroupId, resourceId) {
    try {
        const response = await fetch(`/api/business-context/board-resources/${boardResourceId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                group_id: newGroupId
            })
        });
        
        const data = await response.json();
        
        // Update costs for ALL groups containing clones of this resource
        // Pass oldGroupId to ensure it's updated even if resource was removed from it
        if (resourceId) {
            await updateCostsForAllGroupsWithResource(resourceId, oldGroupId);
        } else {
            // Fallback: Update just the affected groups if resourceId not provided
            if (oldGroupId) {
                await updateGroupCost(oldGroupId);
            }
            if (newGroupId) {
                await updateGroupCost(newGroupId);
            }
        }
        
    } catch (error) {
        console.error('Error updating resource group assignment:', error);
    }
}

/**
 * Update group cost badge
 */
async function updateGroupCost(groupDbId) {
    if (!groupDbId) return;
    
    try {
        const response = await fetch(`/api/business-context/groups/${groupDbId}/cost`);
        const data = await response.json();
        
        if (data.success) {
            const calculatedCost = data.calculated_cost || 0;
            console.log('💰 Group cost updated:', {
                groupId: groupDbId,
                dailyCost: calculatedCost,
                monthlyCost: (calculatedCost * 30).toFixed(2),
                resourceCount: data.resource_count
            });
            
            // Find group object on canvas and update cost display
            const objects = fabricCanvas.getObjects();
            
            for (const obj of objects) {
                if (obj.objectType === 'group' && obj.dbId === groupDbId) {
                    obj.calculatedCost = calculatedCost;
                    
                    // Update cost badge text (children[2] in the fabric.Group)
                    const children = obj.getObjects();
                    const costBadge = children[2]; // [0]=rect, [1]=text, [2]=cost
                    
                    if (costBadge) {
                        const monthlyCost = calculatedCost * 30;
                        const costText = monthlyCost > 0 ? `${monthlyCost.toFixed(2)} ₽/мес` : '0 ₽/мес';
                        costBadge.set('text', costText);
                    }
                    
                    fabricCanvas.renderAll();
                    break;
                }
            }
        }
    } catch (error) {
        console.error('❌ Error updating group cost:', error);
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
async function showResourceInfo(resourceId) {
    const modal = document.getElementById('resourceInfoModal');
    const content = document.getElementById('resourceInfoContent');
    
    // Show modal with loading state
    modal.classList.add('active');
    content.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i></div>';
    
    try {
        // Find resource data
        let resource = null;
        for (const provider of allResources) {
            const found = provider.resources.find(r => r.id === resourceId);
            if (found) {
                resource = {
                    ...found,
                    provider_name: provider.provider_name
                };
                break;
            }
        }
        
        if (!resource) {
            content.innerHTML = '<p class="text-error">Ресурс не найден</p>';
            return;
        }
        
        // Build info HTML
        const html = `
            <div class="resource-info-section">
                <h4>Основная информация</h4>
                <div class="resource-info-grid">
                    <div class="resource-info-label">Название:</div>
                    <div class="resource-info-value">${escapeHtml(resource.name)}</div>
                    
                    <div class="resource-info-label">Тип:</div>
                    <div class="resource-info-value">${escapeHtml(resource.type)}</div>
                    
                    <div class="resource-info-label">Провайдер:</div>
                    <div class="resource-info-value">${escapeHtml(resource.provider_name)}</div>
                    
                    <div class="resource-info-label">IP-адрес:</div>
                    <div class="resource-info-value">${escapeHtml(resource.ip || 'Не указан')}</div>
                    
                    <div class="resource-info-label">Регион:</div>
                    <div class="resource-info-value">${escapeHtml(resource.region || 'Не указан')}</div>
                    
                    <div class="resource-info-label">Статус:</div>
                    <div class="resource-info-value">${escapeHtml(resource.status || 'Неизвестно')}</div>
                </div>
            </div>
            
            <div class="resource-info-section">
                <h4>Стоимость</h4>
                <div class="resource-info-grid">
                    <div class="resource-info-label">Ежемесячно:</div>
                    <div class="resource-info-value">${resource.daily_cost ? (resource.daily_cost * 30).toFixed(2) + ' ₽/мес' : 'Не указана'}</div>
                    
                    <div class="resource-info-label">Ежедневно:</div>
                    <div class="resource-info-value">${resource.daily_cost ? resource.daily_cost.toFixed(2) + ' ₽/день' : 'Не указана'}</div>
                </div>
            </div>
            
            ${resource.created_at ? `
            <div class="resource-info-section">
                <h4>Даты</h4>
                <div class="resource-info-grid">
                    <div class="resource-info-label">Создан:</div>
                    <div class="resource-info-value">${new Date(resource.created_at).toLocaleString('ru-RU')}</div>
                    
                    ${resource.last_sync ? `
                    <div class="resource-info-label">Последняя синхронизация:</div>
                    <div class="resource-info-value">${new Date(resource.last_sync).toLocaleString('ru-RU')}</div>
                    ` : ''}
                </div>
            </div>
            ` : ''}
        `;
        
        content.innerHTML = html;
    } catch (error) {
        console.error('Error showing resource info:', error);
        content.innerHTML = '<p class="text-error">Ошибка загрузки информации</p>';
    }
}

/**
 * Close resource info modal
 */
function closeResourceInfoModal() {
    document.getElementById('resourceInfoModal').classList.remove('active');
}

/**
 * Show resource notes modal
 */
async function showResourceNotes(resourceId) {
    const modal = document.getElementById('resourceNotesModal');
    const header = document.getElementById('resourceNotesHeader');
    const textarea = document.getElementById('resourceNotesText');
    
    console.log('Opening notes for resource ID:', resourceId);
    
    // Store resource ID for save
    textarea.dataset.resourceId = resourceId;
    
    // Find resource data
    let resource = null;
    for (const provider of allResources) {
        const found = provider.resources.find(r => r.id === resourceId);
        if (found) {
            resource = {
                ...found,
                provider_name: provider.provider_name
            };
            break;
        }
    }
    
    console.log('Found resource:', resource);
    
    if (!resource) {
        showFlashMessage('error', 'Ресурс не найден');
        return;
    }
    
    // Set header
    header.innerHTML = `
        <i class="fa-solid fa-server"></i>
        <div class="resource-notes-header-text">
            <div class="resource-notes-header-title">${escapeHtml(resource.name)}</div>
            <div class="resource-notes-header-meta">${escapeHtml(resource.type)} • ${escapeHtml(resource.provider_name)}</div>
        </div>
    `;
    
    // Load existing notes from resource
    console.log('Loading notes for resource:', { id: resource.id, name: resource.name, notes: resource.notes });
    textarea.value = resource.notes || '';
    
    // Show modal
    modal.classList.add('active');
    textarea.focus();
}

/**
 * Close resource notes modal
 */
function closeResourceNotesModal() {
    const modal = document.getElementById('resourceNotesModal');
    const textarea = document.getElementById('resourceNotesText');
    
    // Clear textarea when closing
    textarea.value = '';
    textarea.dataset.resourceId = '';
    
    // Hide modal
    modal.classList.remove('active');
}

/**
 * Save resource notes (system-wide, not board-specific)
 */
async function saveResourceNotes() {
    const textarea = document.getElementById('resourceNotesText');
    const resourceId = parseInt(textarea.dataset.resourceId);
    const notes = textarea.value;
    
    console.log('Saving notes for resource:', { resourceId, notes });
    
    try {
        const response = await fetch(`/api/business-context/resources/${resourceId}/notes`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: notes })
        });
        
        const data = await response.json();
        console.log('Save response:', data);
        
        if (data.success) {
            console.log('Notes saved successfully! Reloading resources...');
            
            // Close modal
            closeResourceNotesModal();
            
            // Reload resources to update "has notes" indicator in toolbox
            await loadResources();
            
            // Update notes icon on canvas for all instances of this resource
            const hasNotes = data.has_notes;
            const objects = fabricCanvas.getObjects();
            const resourceGroups = objects.filter(obj => 
                obj.objectType === 'resource' && obj.resourceId === resourceId
            );
            
            resourceGroups.forEach(resourceGroup => {
                // Access notes icon from group's children (index 5 and 6)
                const children = resourceGroup.getObjects();
                const notesIcon = children[5];  // notesIconCircle
                const notesIconText = children[6];  // notesIconText
                
                if (notesIcon && notesIconText) {
                    // Update to solid colored badge (green when has notes, gray when empty)
                    notesIcon.set({
                        fill: hasNotes ? '#10B981' : '#9CA3AF'
                    });
                    // Icon text is always white on colored background
                    notesIconText.set({
                        fill: '#FFFFFF'
                    });
                }
            });
            
            fabricCanvas.renderAll();
            
            console.log('Resources reloaded and canvas updated');
        } else {
            showFlashMessage('error', data.error || 'Ошибка сохранения заметок');
        }
    } catch (error) {
        console.error('Error saving notes:', error);
        showFlashMessage('error', 'Ошибка сохранения заметок');
    }
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
    // Skip autosave for demo users
    if (window.isDemoUser) {
        const indicator = document.getElementById('saveIndicator');
        indicator.textContent = 'Демо режим';
        indicator.className = 'save-indicator demo-mode';
        return;
    }
    
    const indicator = document.getElementById('saveIndicator');
    indicator.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i>';
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
    
    // Prevent demo users from saving
    if (window.isDemoUser) {
        const indicator = document.getElementById('saveIndicator');
        indicator.textContent = 'Демо режим';
        indicator.className = 'save-indicator demo-mode';
        if (!isAutoSave) {
            showFlashMessage('info', 'В демо режиме изменения не сохраняются');
        }
        return;
    }
    
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
        
        // Check for authentication errors
        if (handleApiError(response, data)) {
            indicator.textContent = 'Не авторизован';
            indicator.className = 'save-indicator';
            return;
        }
        
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
 * Check if resources moved outside a group and update their assignment
 */
async function checkAndUpdateResourcesOutsideGroup(businessGroup) {
    if (!businessGroup.dbId) return;
    
    console.log('🔍 Checking resource-group assignments for group', businessGroup.dbId);
    
    // Get group bounds
    const groupBounds = businessGroup.getBoundingRect();
    
    // Find all resources on canvas
    const allResources = fabricCanvas.getObjects().filter(obj => obj.objectType === 'resource');
    
    // Track which resources were moved (resourceId -> oldGroupId)
    const affectedResources = new Map();
    
    for (const resource of allResources) {
        // Get resource center point
        const resourceCenter = resource.getCenterPoint();
        
        // Check if resource center is inside group bounds
        const isInside = (
            resourceCenter.x >= groupBounds.left &&
            resourceCenter.x <= groupBounds.left + groupBounds.width &&
            resourceCenter.y >= groupBounds.top &&
            resourceCenter.y <= groupBounds.top + groupBounds.height
        );
        
        // Case 1: Resource is assigned to this group but is now OUTSIDE
        if (resource.groupId === businessGroup.dbId && !isInside) {
            console.log('   ⚠️ Resource', resource.resourceId, 'is now OUTSIDE group', businessGroup.dbId);
            
            // Resource moved outside - unassign from group
            try {
                const oldGroupId = resource.groupId;  // Save before clearing
                
                const response = await fetch(`/api/business-context/board-resources/${resource.boardResourceId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        group_id: null
                    })
                });
                
                const data = await response.json();
                
                // Check for authentication errors
                if (handleApiError(response, data)) return;
                
                if (data.success) {
                    resource.groupId = null;
                    affectedResources.set(resource.resourceId, oldGroupId);  // Track old group
                    console.log('   ✅ Resource unassigned from group');
                }
            } catch (error) {
                console.error('Error unassigning resource from group:', error);
            }
        }
        
        // Case 2: Resource is NOT assigned to this group but is now INSIDE
        else if (resource.groupId !== businessGroup.dbId && isInside) {
            console.log('   ✅ Resource', resource.resourceId, 'is now INSIDE group', businessGroup.dbId);
            
            // Resource moved inside - assign to group
            try {
                const oldGroupId = resource.groupId;  // Save before changing
                
                const response = await fetch(`/api/business-context/board-resources/${resource.boardResourceId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        group_id: businessGroup.dbId
                    })
                });
                
                const data = await response.json();
                
                // Check for authentication errors
                if (handleApiError(response, data)) return;
                
                if (data.success) {
                    resource.groupId = businessGroup.dbId;
                    affectedResources.set(resource.resourceId, oldGroupId);  // Track old group
                    console.log('   ✅ Resource assigned to group');
                }
            } catch (error) {
                console.error('Error assigning resource to group:', error);
            }
        }
    }
    
    // Update costs for all groups containing any affected resources
    if (affectedResources.size > 0) {
        console.log(`   💰 Recalculating costs for ${affectedResources.size} affected resources`);
        for (const [resourceId, oldGroupId] of affectedResources) {
            await updateCostsForAllGroupsWithResource(resourceId, oldGroupId);
        }
    }
}

/**
 * Check if a group intersects with any other groups on the canvas
 */
function checkGroupIntersection(group, excludeGroup = null) {
    const groupBounds = {
        left: group.left,
        top: group.top,
        right: group.left + group.width,
        bottom: group.top + group.height
    };
    
    // Get all groups on canvas
    const allGroups = fabricCanvas.getObjects().filter(obj => 
        obj.objectType === 'group' && obj !== excludeGroup
    );
    
    console.log('      🔍 checkGroupIntersection:', {
        checkingGroup: { left: group.left, top: group.top, width: group.width, height: group.height },
        otherGroupsCount: allGroups.length
    });
    
    for (const otherGroup of allGroups) {
        const otherBounds = {
            left: otherGroup.left,
            top: otherGroup.top,
            right: otherGroup.left + otherGroup.width,
            bottom: otherGroup.top + otherGroup.height
        };
        
        // Check for intersection
        const intersects = !(
            groupBounds.right < otherBounds.left ||
            groupBounds.left > otherBounds.right ||
            groupBounds.bottom < otherBounds.top ||
            groupBounds.top > otherBounds.bottom
        );
        
        if (intersects) {
            console.log('         💥 Intersection with group at:', otherBounds);
            return true; // Intersection found
        }
    }
    
    console.log('         ✓ No intersection');
    return false; // No intersection
}

/**
 * Find a non-overlapping position for a new group
 * Shifts the group right and down until a valid position is found
 */
function findNonOverlappingPosition(initialLeft, initialTop, width, height) {
    const shiftAmount = 30; // Amount to shift right/down on each attempt
    const maxAttempts = 20; // Prevent infinite loop
    
    let left = initialLeft;
    let top = initialTop;
    let attempts = 0;
    
    // Create a temporary group object for collision testing
    const tempGroup = {
        left: left,
        top: top,
        width: width,
        height: height
    };
    
    // Keep shifting until we find a non-overlapping position
    while (checkGroupIntersection(tempGroup) && attempts < maxAttempts) {
        left += shiftAmount;
        top += shiftAmount;
        tempGroup.left = left;
        tempGroup.top = top;
        attempts++;
    }
    
    return { left, top };
}

/**
 * Create a new group on canvas
 */
async function createGroupOnCanvas(x, y) {
    if (!fabricCanvas || !currentBoard) return;
    
    // Save state BEFORE creating the group (so undo can restore to this state)
    saveToUndoStack();
    
    // Set flag to prevent intermediate saves during object creation
    isCreatingObjects = true;
    
    // Generate unique fabric_id
    const fabricId = 'group_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // If no coordinates provided, use canvas center
    let posX, posY;
    if (x !== undefined && y !== undefined) {
        posX = x;
        posY = y;
    } else {
        // Get canvas center position
        const zoom = fabricCanvas.getZoom();
        const vpt = fabricCanvas.viewportTransform;
        posX = (fabricCanvas.width / 2 - vpt[4]) / zoom;
        posY = (fabricCanvas.height / 2 - vpt[5]) / zoom;
    }
    
    // Define group dimensions
    const groupWidth = 300;
    const groupHeight = 200;
    
    // Calculate initial position (centered on click point)
    let initialLeft = posX - groupWidth / 2;
    let initialTop = posY - groupHeight / 2;
    
    // Find a non-overlapping position
    const adjustedPosition = findNonOverlappingPosition(initialLeft, initialTop, groupWidth, groupHeight);
    
    // Create group rectangle (background)
    const groupRect = new fabric.Rect({
        left: 0,
        top: 0,
        width: groupWidth,
        height: groupHeight,
        fill: 'rgba(146, 64, 14, 0.05)',
        stroke: '#92400E',
        strokeWidth: 2,
        rx: 4,
        ry: 4
    });
    
    // Create group name text (positioned relative to rectangle)
    const groupText = new fabric.Text('Новая группа', {
        left: 10,
        top: 10,
        fontSize: 16,
        fontWeight: 'bold',
        fill: '#1F2937'
    });
    
    // Create cost badge text (positioned relative to rectangle)
    const costBadge = new fabric.Text('0 ₽/мес', {
        left: groupWidth - 80,
        top: 10,
        fontSize: 14,
        fontWeight: '600',
        fill: '#10B981'
    });
    
    // Create Fabric.js Group (bundles all 3 objects together)
    const businessGroup = new fabric.Group([groupRect, groupText, costBadge], {
        left: adjustedPosition.left,
        top: adjustedPosition.top,
        selectable: true,
        hasControls: true,
        hasBorders: true,
        lockRotation: true,
        hasRotate: false,
        subTargetCheck: true, // Allow clicking on children for double-click edit
        // Custom properties for our business logic
        objectType: 'group',
        fabricId: fabricId,
        groupName: 'Новая группа',
        groupColor: '#92400E',
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
        })(fabric.Group.prototype.toObject)
    });
    
    // Add group to canvas (all 3 objects as one unit!)
    fabricCanvas.add(businessGroup);
    
    // Send group to back (groups should always be behind resources)
    businessGroup.sendToBack();
    
    // Hide rotation control handle
    businessGroup.setControlVisible('mtr', false);
    
    // Store initial position and scale for collision detection
    businessGroup.lastValidLeft = businessGroup.left;
    businessGroup.lastValidTop = businessGroup.top;
    businessGroup.lastValidScaleX = businessGroup.scaleX || 1;
    businessGroup.lastValidScaleY = businessGroup.scaleY || 1;
    
    // Handle moving with collision detection
    businessGroup.on('moving', function() {
        console.log('🔵 Group moving event fired', {
            fabricId: this.fabricId,
            currentPos: { left: this.left, top: this.top },
            lastValidPos: { left: this.lastValidLeft, top: this.lastValidTop }
        });
        
        // Check for intersection with other groups
        if (checkGroupIntersection(this, this)) {
            console.log('⚠️ Collision detected! Reverting to last valid position');
            // Revert to last valid position
            this.set({
                left: this.lastValidLeft,
                top: this.lastValidTop
            });
            console.log('   Reverted to:', { left: this.left, top: this.top });
        } else {
            console.log('✅ No collision, storing position');
            // Store current position as valid
            this.lastValidLeft = this.left;
            this.lastValidTop = this.top;
        }
        // No need to update children - they move automatically with the group! ✨
    });
    
    // When group movement finishes, check if any resources moved outside
    businessGroup.on('modified', async function() {
        console.log('✅ GROUP MODIFIED (finished):', {
            id: this.fabricId,
            final: {
                width: this.width,
                height: this.height,
                scaleX: this.scaleX,
                scaleY: this.scaleY,
                left: this.left,
                top: this.top
            },
            boundingRect: this.getBoundingRect()
        });
        
        // Keep group at the back (behind all resources)
        this.sendToBack();
        
        // Update coordinates after modification to ensure selection boundary stays aligned
        this.setCoords();
        console.log('   Final setCoords() called in modified event');
        console.log('   Final bounding rect:', this.getBoundingRect());
        
        await checkAndUpdateResourcesOutsideGroup(this);
        updateGroupInDatabase(this);
    });
    
    businessGroup.on('scaling', function() {
        console.log('📏 GROUP SCALING:', {
            id: this.fabricId,
            scaleX: this.scaleX,
            scaleY: this.scaleY,
            boundingRect: this.getBoundingRect()
        });
        
        // For fabric.Group, DON'T normalize scale - let it keep scaleX/scaleY
        // The children will scale automatically
        
        // Check for intersection using current scaled bounds
        if (checkGroupIntersection(this, this)) {
            console.log('   ❌ Intersection - reverting to last valid scale');
            // Revert to last valid scale
            this.set({
                scaleX: this.lastValidScaleX || 1,
                scaleY: this.lastValidScaleY || 1
            });
            this.setCoords();
        } else {
            console.log('   ✅ No intersection');
            // Store current scale as valid
            this.lastValidScaleX = this.scaleX;
            this.lastValidScaleY = this.scaleY;
        }
    });
    
    // Double-click to edit name
    businessGroup.on('mousedblclick', function() {
        editGroupName(this);
    });
    
    fabricCanvas.renderAll();
    
    // Save group to database
    await saveGroupToDatabase(businessGroup);
    
    // Re-enable automatic saves
    isCreatingObjects = false;
    
    scheduleAutoSave();
}

/**
 * Create text object on canvas
 */
function createTextOnCanvas(x, y) {
    if (!fabricCanvas || !currentBoard) return;
    
    // Save state BEFORE creating text (so undo can restore to this state)
    saveToUndoStack();
    
    // Set flag to prevent intermediate saves during object creation
    isCreatingObjects = true;
    
    // If no coordinates provided, use canvas center
    let posX, posY;
    if (x !== undefined && y !== undefined) {
        posX = x;
        posY = y;
    } else {
        // Get canvas center position
        const zoom = fabricCanvas.getZoom();
        const vpt = fabricCanvas.viewportTransform;
        posX = (fabricCanvas.width / 2 - vpt[4]) / zoom;
        posY = (fabricCanvas.height / 2 - vpt[5]) / zoom;
    }
    
    // Create text object
    const text = new fabric.IText('Текст', {
        left: posX - 50,
        top: posY - 20,
        fontSize: 24,
        fontFamily: 'Arial, sans-serif',
        fill: '#1F2937',
        objectType: 'freeText',
        selectable: true,
        editable: true,
        lockRotation: true,
        hasRotate: false
    });
    
    // Add to canvas
    fabricCanvas.add(text);
    
    // Hide rotation control handle
    text.setControlVisible('mtr', false);
    
    fabricCanvas.setActiveObject(text);
    
    // Enter edit mode immediately
    text.enterEditing();
    text.selectAll();
    
    fabricCanvas.renderAll();
    
    // Re-enable automatic saves
    isCreatingObjects = false;
    
    scheduleAutoSave();
}

/**
 * Create rectangle object on canvas
 */
function createRectangleOnCanvas(x, y) {
    if (!fabricCanvas || !currentBoard) return;
    
    // Save state BEFORE creating rectangle (so undo can restore to this state)
    saveToUndoStack();
    
    // Set flag to prevent intermediate saves during object creation
    isCreatingObjects = true;
    
    // If no coordinates provided, use canvas center
    let posX, posY;
    if (x !== undefined && y !== undefined) {
        posX = x;
        posY = y;
    } else {
        // Get canvas center position
        const zoom = fabricCanvas.getZoom();
        const vpt = fabricCanvas.viewportTransform;
        posX = (fabricCanvas.width / 2 - vpt[4]) / zoom;
        posY = (fabricCanvas.height / 2 - vpt[5]) / zoom;
    }
    
    // Create rectangle object
    const rect = new fabric.Rect({
        left: posX - 100,
        top: posY - 60,
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
        hasBorders: true,
        lockRotation: true,
        hasRotate: false
    });
    
    // Add to canvas
    fabricCanvas.add(rect);
    
    // Hide rotation control handle
    rect.setControlVisible('mtr', false);
    
    fabricCanvas.setActiveObject(rect);
    
    fabricCanvas.renderAll();
    
    // Re-enable automatic saves
    isCreatingObjects = false;
    
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
            // Create group rectangle (background)
            const groupRect = new fabric.Rect({
                left: 0,
                top: 0,
                width: group.size.width,
                height: group.size.height,
                fill: hexToRgba(group.color, 0.05),
                stroke: group.color,
                strokeWidth: 2,
                rx: 4,
                ry: 4
            });
            
            // Create group name text (positioned relative to rectangle)
            const groupText = new fabric.Text(group.name, {
                left: 10,
                top: 10,
                fontSize: 16,
                fontWeight: 'bold',
                fill: '#1F2937'
            });
            
            // Create cost badge text (positioned relative to rectangle)
            const monthlyCost = (group.calculated_cost || 0) * 30;
            const costText = monthlyCost > 0 ? `${monthlyCost.toFixed(2)} ₽/мес` : '0 ₽/мес';
            const costBadge = new fabric.Text(costText, {
                left: group.size.width - 80,
                top: 10,
                fontSize: 14,
                fontWeight: '600',
                fill: '#10B981'
            });
            
            // Create Fabric.js Group (bundles all 3 objects together)
            const businessGroup = new fabric.Group([groupRect, groupText, costBadge], {
                left: group.position.x,
                top: group.position.y,
                selectable: true,
                hasControls: true,
                hasBorders: true,
                lockRotation: true,
                hasRotate: false,
                subTargetCheck: true,
                // Custom properties for our business logic
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
                })(fabric.Group.prototype.toObject)
            });
            
            // Add to canvas
            fabricCanvas.add(businessGroup);
            
            // Send group to back (groups should always be behind resources)
            businessGroup.sendToBack();
            
            // Hide rotation control handle
            businessGroup.setControlVisible('mtr', false);
            
            // Store initial position and scale for collision detection
            businessGroup.lastValidLeft = businessGroup.left;
            businessGroup.lastValidTop = businessGroup.top;
            businessGroup.lastValidScaleX = businessGroup.scaleX || 1;
            businessGroup.lastValidScaleY = businessGroup.scaleY || 1;
            
            // Setup event handlers
            businessGroup.on('moving', function() {
                console.log('🔵 [LOADED] Group moving event fired', {
                    fabricId: this.fabricId,
                    currentPos: { left: this.left, top: this.top },
                    lastValidPos: { left: this.lastValidLeft, top: this.lastValidTop }
                });
                
                // Check for intersection with other groups
                if (checkGroupIntersection(this, this)) {
                    console.log('⚠️ [LOADED] Collision detected! Reverting');
                    // Revert to last valid position
                    this.set({
                        left: this.lastValidLeft,
                        top: this.lastValidTop
                    });
                } else {
                    console.log('✅ [LOADED] No collision');
                    // Store current position as valid
                    this.lastValidLeft = this.left;
                    this.lastValidTop = this.top;
                }
                // No need to update children - they move automatically! ✨
            });
            
            businessGroup.on('scaling', function() {
                console.log('📏 GROUP SCALING:', {
                    id: this.fabricId,
                    scaleX: this.scaleX,
                    scaleY: this.scaleY,
                    boundingRect: this.getBoundingRect()
                });
                
                // For fabric.Group, DON'T normalize scale - let it keep scaleX/scaleY
                // The children will scale automatically
                
                // Check for intersection using current scaled bounds
                if (checkGroupIntersection(this, this)) {
                    console.log('   ❌ Intersection - reverting to last valid scale');
                    // Revert to last valid scale
                    this.set({
                        scaleX: this.lastValidScaleX || 1,
                        scaleY: this.lastValidScaleY || 1
                    });
                    this.setCoords();
                } else {
                    console.log('   ✅ No intersection');
                    // Store current scale as valid
                    this.lastValidScaleX = this.scaleX;
                    this.lastValidScaleY = this.scaleY;
                }
            });
            
            // When group movement/resize finishes, check if resources moved outside
            businessGroup.on('modified', async function() {
                console.log('✅ GROUP MODIFIED (finished, loaded):', {
                    id: this.fabricId,
                    final: {
                        width: this.width,
                        height: this.height,
                        scaleX: this.scaleX,
                        scaleY: this.scaleY,
                        left: this.left,
                        top: this.top
                    },
                    boundingRect: this.getBoundingRect()
                });
                
                // Keep group at the back (behind all resources)
                this.sendToBack();
                
                // Update coordinates after modification to ensure selection boundary stays aligned
                this.setCoords();
                console.log('   Final setCoords() called in modified event');
                console.log('   Final bounding rect:', this.getBoundingRect());
                
                await checkAndUpdateResourcesOutsideGroup(this);
                updateGroupInDatabase(this);
            });
            
            businessGroup.on('mousedblclick', function() {
                editGroupName(this);
            });
        } catch (error) {
            console.error('Error loading group:', error);
        }
    });
    
    fabricCanvas.renderAll();
}

/**
 * Load placed resources from board data and render on canvas
 */
function loadResourcesOnCanvas(boardResources) {
    if (!fabricCanvas || !boardResources) {
        return;
    }
    
    boardResources.forEach(boardResource => {
        try {
            const resourceData = boardResource.resource;
            if (!resourceData) {
                console.warn('Board resource missing resource data:', boardResource);
                return;
            }
            
            // Convert API data format to match expected format
            const formattedResource = {
                id: resourceData.id,
                name: resourceData.name || 'Unknown',
                type: resourceData.type || 'Resource',
                ip: resourceData.ip || null,
                notes: resourceData.notes || null,
                has_notes: resourceData.has_notes || false
            };
            
            // Create resource object on canvas
            // Pass true for isAbsolutePosition since we're loading saved positions
            createResourceObject(
                formattedResource,
                boardResource.position.x,
                boardResource.position.y,
                boardResource.id,
                boardResource.group_id,
                true  // isAbsolutePosition
            );
        } catch (error) {
            console.error('Error loading resource:', error, boardResource);
        }
    });
    
    // Update clone badges for all resources after loading
    const uniqueResourceIds = new Set();
    boardResources.forEach(br => {
        if (br.resource && br.resource.id) {
            uniqueResourceIds.add(br.resource.id);
        }
    });
    uniqueResourceIds.forEach(resourceId => {
        updateCloneBadges(resourceId);
    });
    
    fabricCanvas.renderAll();
}

/**
 * Edit group name
 */
function editGroupName(businessGroup) {
    const currentName = businessGroup.groupName || 'Новая группа';
    const newName = prompt('Введите название группы:', currentName);
    
    if (newName && newName.trim()) {
        // Update group property
        businessGroup.groupName = newName.trim();
        
        // Update the text child (children[1] is the name text)
        const groupText = businessGroup.getObjects()[1];
        if (groupText) {
            groupText.set('text', newName.trim());
        }
        
        fabricCanvas.renderAll();
        
        // Update in database
        updateGroupInDatabase(businessGroup);
        scheduleAutoSave();
    }
}

/**
 * Change group color
 * @deprecated This function is replaced by the properties panel.
 * Use showPropertiesPanel() instead.
 */
function changeGroupColor(businessGroup) {
    const colors = [
        { name: 'Коричневый', value: '#92400E' },
        { name: 'Зелёный', value: '#10B981' },
        { name: 'Фиолетовый', value: '#8B5CF6' },
        { name: 'Оранжевый', value: '#F59E0B' },
        { name: 'Красный', value: '#EF4444' },
        { name: 'Розовый', value: '#EC4899' },
        { name: 'Синий', value: '#3B82F6' },
        { name: 'Серый', value: '#6B7280' }
    ];
    
    const colorOptions = colors.map((c, i) => `${i + 1}. ${c.name}`).join('\n');
    const choice = prompt(`Выберите цвет (1-${colors.length}):\n\n${colorOptions}`);
    
    const index = parseInt(choice) - 1;
    if (index >= 0 && index < colors.length) {
        const newColor = colors[index].value;
        businessGroup.groupColor = newColor;
        
        // Update the background rectangle child (children[0])
        const children = businessGroup.getObjects();
        const groupRect = children[0];
        if (groupRect) {
            groupRect.set({
                stroke: newColor,
                fill: hexToRgba(newColor, 0.05)
            });
        }
        
        fabricCanvas.renderAll();
        
        // Update in database
        updateGroupInDatabase(businessGroup);
        scheduleAutoSave();
    }
}

/**
 * NOTE: updateGroupChildren() and updateGroupChildrenByFabricId() are NO LONGER NEEDED!
 * fabric.Group automatically keeps children in sync - this was causing ghost objects!
 */

/**
 * Save group to database
 */
async function saveGroupToDatabase(groupRect) {
    if (!currentBoard) return;
    
    try {
        // Get actual dimensions from bounding rect (accounts for scale)
        const bounds = groupRect.getBoundingRect();
        
        const response = await fetch(`/api/business-context/boards/${currentBoard.id}/groups`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: groupRect.groupName,
                fabric_id: groupRect.fabricId,
                position_x: bounds.left,
                position_y: bounds.top,
                width: bounds.width,
                height: bounds.height,
                color: groupRect.groupColor || '#3B82F6'
            })
        });
        
        const data = await response.json();
        
        // Check for authentication errors
        if (handleApiError(response, data)) return;
        
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
        // Get actual dimensions from bounding rect (accounts for scale)
        const bounds = groupRect.getBoundingRect();
        
        const response = await fetch(`/api/business-context/groups/${groupRect.dbId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: groupRect.groupName,
                position_x: bounds.left,
                position_y: bounds.top,
                width: bounds.width,
                height: bounds.height,
                color: groupRect.groupColor || '#3B82F6'
            })
        });
        
        const data = await response.json();
        
        // Check for authentication errors
        if (handleApiError(response, data)) return;
        
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
async function deleteGroup(businessGroup) {
    if (!businessGroup.dbId) return;
    
    try {
        const response = await fetch(`/api/business-context/groups/${businessGroup.dbId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Remove from canvas (removes the entire group with all children automatically!)
            fabricCanvas.remove(businessGroup);
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
 * Delete resource from board
 */
async function deleteResourceFromBoard(resourceGroup) {
    if (!resourceGroup.boardResourceId) return;
    
    try {
        const response = await fetch(`/api/business-context/board-resources/${resourceGroup.boardResourceId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            const resourceId = resourceGroup.resourceId;
            const oldGroupId = resourceGroup.groupId;
            
            // Remove the entire resource group (all child elements removed automatically)
            fabricCanvas.remove(resourceGroup);
            fabricCanvas.renderAll();
            
            // Update clone badges for remaining instances of this resource
            updateCloneBadges(resourceId);
            
            // Reload resources to update toolbox (resource should show as available again)
            await loadResources();
            
            // Update costs for all groups containing this resource
            // Pass oldGroupId to ensure the group this resource was in gets updated
            await updateCostsForAllGroupsWithResource(resourceId, oldGroupId);
            
            scheduleAutoSave();
        } else {
            showFlashMessage('error', data.error || 'Не удалось удалить ресурс');
        }
    } catch (error) {
        console.error('Error deleting resource:', error);
        showFlashMessage('error', 'Не удалось удалить ресурс');
    }
}

/**
 * Count how many instances of a resource are on the canvas
 */
function countResourceClones(resourceId) {
    const objects = fabricCanvas.getObjects();
    return objects.filter(obj => obj.objectType === 'resource' && obj.resourceId === resourceId).length;
}

/**
 * Update clone badges for all instances of a resource
 */
function updateCloneBadges(resourceId) {
    const objects = fabricCanvas.getObjects();
    const resourceInstances = objects.filter(obj => obj.objectType === 'resource' && obj.resourceId === resourceId);
    
    const hasClones = resourceInstances.length > 1;
    
    resourceInstances.forEach(resourceGroup => {
        // Access badge elements from the group's child array
        const children = resourceGroup.getObjects();
        const cloneBadge = children[7];  // cloneBadgeCircle is index 7
        const cloneBadgeText = children[8];  // cloneBadgeText is index 8
        
        if (hasClones) {
            // Show badge
            if (cloneBadge) cloneBadge.set({ visible: true });
            if (cloneBadgeText) cloneBadgeText.set({ visible: true });
        } else {
            // Hide badge
            if (cloneBadge) cloneBadge.set({ visible: false });
            if (cloneBadgeText) cloneBadgeText.set({ visible: false });
        }
    });
    
    fabricCanvas.renderAll();
}

/**
 * Update costs for all groups containing clones of a specific resource
 * Also updates oldGroupId if provided (for when resource is removed from a group)
 */
async function updateCostsForAllGroupsWithResource(resourceId, oldGroupId = null) {
    if (!resourceId) return;
    
    const objects = fabricCanvas.getObjects();
    const resourceInstances = objects.filter(obj => 
        obj.objectType === 'resource' && obj.resourceId === resourceId
    );
    
    // Get unique group IDs that contain this resource
    const groupIds = new Set();
    resourceInstances.forEach(resource => {
        if (resource.groupId) {
            groupIds.add(resource.groupId);
        }
    });
    
    // Also include the old group if provided (important when resource was just removed)
    if (oldGroupId) {
        groupIds.add(oldGroupId);
    }
    
    // Update cost for each group
    console.log(`💰 Updating costs for ${groupIds.size} groups containing resource ${resourceId}`);
    for (const groupId of groupIds) {
        await updateGroupCost(groupId);
    }
}

/**
 * Clone resource on canvas
 */
async function cloneResource(resourceCard) {
    if (!resourceCard.resourceId || !currentBoard) return;
    
    try {
        // Save state before cloning
        saveToUndoStack();
        isCreatingObjects = true;
        
        // Create offset position for the clone (50px down and right)
        const cloneX = resourceCard.left + 50;
        const cloneY = resourceCard.top + 50;
        
        // Check if dropped inside a group
        const groupId = getGroupAtPosition(cloneX, cloneY);
        
        // Save clone to database (allows multiple placements of same resource)
        const response = await fetch(`/api/business-context/boards/${currentBoard.id}/resources`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resource_id: resourceCard.resourceId,
                position_x: cloneX,
                position_y: cloneY,
                group_id: groupId
            })
        });
        
        const data = await response.json();
        
        // Check for authentication errors
        if (handleApiError(response, data)) {
            isCreatingObjects = false;
            return;
        }
        
        if (data.success) {
            // Get resource data
            let resourceData = null;
            for (const provider of allResources) {
                const found = provider.resources.find(r => r.id === resourceCard.resourceId);
                if (found) {
                    resourceData = found;
                    break;
                }
            }
            
            if (!resourceData) {
                showFlashMessage('error', 'Resource data not found');
                isCreatingObjects = false;
                return;
            }
            
            // Create the resource object on canvas
            createResourceObject(resourceData, cloneX, cloneY, data.board_resource.id, groupId, true);
            
            // Update clone badges for all instances of this resource
            updateCloneBadges(resourceCard.resourceId);
            
            // Update costs for ALL groups containing this resource (not just the new one)
            // This ensures cost splitting is recalculated across all groups
            await updateCostsForAllGroupsWithResource(resourceCard.resourceId);
            
            // Reload resources to update toolbox
            await loadResources();
            
            showFlashMessage('success', 'Ресурс клонирован');
        } else {
            showFlashMessage('error', data.error || 'Не удалось клонировать ресурс');
        }
        
        isCreatingObjects = false;
        scheduleAutoSave();
    } catch (error) {
        console.error('Error cloning resource:', error);
        showFlashMessage('error', 'Не удалось клонировать ресурс');
        isCreatingObjects = false;
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
    
    // Manual save (Ctrl+S) removed - autosave only
});

/**
 * Show flash message
 */
function showFlashMessage(type, message) {
    // Use existing flash message system from main.js if available
    if (typeof window.showMessage === 'function') {
        window.showMessage(type, message);
    }
    // No fallback alert - visual feedback (badges, placement) is sufficient
}

