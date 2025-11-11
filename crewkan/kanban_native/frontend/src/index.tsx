// Native Kanban Board Component for CrewKan
// Bi-directional Streamlit component with drag-and-drop support

import { Streamlit } from "streamlit-component-lib/dist/streamlit";

// Component state
let columns: any[] = [];
let tasks: any[] = [];
let height: number = 800;
let draggedTask: HTMLElement | null = null;
let draggedFromColumn: string | null = null;

// Initialize component
function initComponent() {
    // Create the main container
    const container = document.createElement('div');
    container.id = 'kanban-container';
    container.className = 'kanban-container';
    document.body.appendChild(container);
    
    // Tell Streamlit we're ready
    Streamlit.setComponentReady();
    
    // Listen for render events from Streamlit
    // Use Streamlit.events instead of window.addEventListener for proper event handling
    Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, (event: any) => {
        const renderData = event.detail;
        const args = renderData.args || {};
        columns = args.columns || [];
        tasks = args.tasks || [];
        height = args.height || 800;
        
        // Set container height
        document.body.style.height = height + 'px';
        container.style.height = height + 'px';
        
        // Update frame height
        Streamlit.setFrameHeight(height);
        
        // Render the board
        renderBoard();
    });
}

// Render the Kanban board
function renderBoard() {
    const container = document.getElementById('kanban-container');
    if (!container) {
        console.error('Kanban container not found');
        return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Group tasks by column
    const tasksByColumn: { [key: string]: any[] } = {};
    columns.forEach(col => {
        tasksByColumn[col.id] = [];
    });
    
    tasks.forEach(task => {
        const colId = task.column || 'todo';
        if (tasksByColumn[colId]) {
            tasksByColumn[colId].push(task);
        }
    });
    
    // Create columns
    columns.forEach(column => {
        const columnDiv = document.createElement('div');
        columnDiv.className = 'kanban-column';
        columnDiv.dataset.columnId = column.id;
        columnDiv.style.borderTop = `3px solid ${column.color || '#3498db'}`;

        // Column header
        const header = document.createElement('div');
        header.className = 'column-header';
        header.style.borderTop = `3px solid ${column.color || '#3498db'}`;
        
        const title = document.createElement('span');
        title.textContent = column.name || column.id;
        header.appendChild(title);
        
        const count = document.createElement('span');
        count.className = 'column-count';
        count.textContent = (tasksByColumn[column.id]?.length || 0).toString();
        header.appendChild(count);
        
        columnDiv.appendChild(header);

        // Column body
        const body = document.createElement('div');
        body.className = 'column-body';

        const columnTasks = tasksByColumn[column.id] || [];
        if (columnTasks.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'empty-column';
            empty.textContent = 'No tasks';
            body.appendChild(empty);
        } else {
            columnTasks.forEach(task => {
                const card = createTaskCard(task, column.id);
                body.appendChild(card);
            });
        }

        columnDiv.appendChild(body);

        // Drag and drop handlers - attach to both column and body
        columnDiv.addEventListener('dragover', handleDragOver);
        columnDiv.addEventListener('drop', handleDrop);
        columnDiv.addEventListener('dragleave', handleDragLeave);
        
        // Also attach to body for drops on empty areas
        body.addEventListener('dragover', handleDragOver);
        body.addEventListener('drop', handleDrop);
        body.addEventListener('dragleave', handleDragLeave);

        container.appendChild(columnDiv);
    });
    
    // Update frame height after rendering
    Streamlit.setFrameHeight(height);
}

// Escape HTML to prevent XSS
function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Create a task card element
function createTaskCard(task: any, columnId: string): HTMLElement {
    const card = document.createElement('div');
    card.className = 'task-card';
    card.draggable = true;
    card.dataset.taskId = task.id;
    card.dataset.columnId = columnId;

    const priority = task.priority || 'medium';
    const priorityClass = `priority-${priority}`;
    const priorityText = priority.charAt(0).toUpperCase() + priority.slice(1);

    const tags = task.tags || [];

    // Task title
    const title = document.createElement('div');
    title.className = 'task-title';
    title.textContent = task.title || 'Untitled';
    card.appendChild(title);

    // Task ID
    if (task.id) {
        const taskId = document.createElement('div');
        taskId.className = 'task-id';
        taskId.textContent = task.id;
        card.appendChild(taskId);
    }

    // Task meta (priority and tags)
    const meta = document.createElement('div');
    meta.className = 'task-meta';
    
    if (priority) {
        const prioritySpan = document.createElement('span');
        prioritySpan.className = `task-priority ${priorityClass}`;
        prioritySpan.textContent = priorityText;
        meta.appendChild(prioritySpan);
    }
    
    if (tags.length > 0) {
        const tagsDiv = document.createElement('div');
        tagsDiv.className = 'task-tags';
        tags.forEach((tag: string) => {
            const tagSpan = document.createElement('span');
            tagSpan.className = 'task-tag';
            tagSpan.textContent = tag;
            tagsDiv.appendChild(tagSpan);
        });
        meta.appendChild(tagsDiv);
    }
    
    card.appendChild(meta);

    // Drag handlers
    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);
    card.addEventListener('click', () => handleTaskClick(task.id));

    return card;
}

function handleTaskClick(taskId: string) {
    sendClickEvent(taskId);
}

// Drag handlers
function handleDragStart(e: DragEvent) {
    if (!e.target) return;
    const target = e.target as HTMLElement;
    draggedTask = target;
    draggedFromColumn = target.dataset.columnId || null;
    target.classList.add('dragging');
    if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', target.outerHTML);
        e.dataTransfer.setData('text/plain', target.dataset.taskId || '');
    }
}

function handleDragOver(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
        e.dataTransfer.dropEffect = 'move';
    }
    
    // Find the column (could be column div or body)
    const column = (e.currentTarget as HTMLElement).closest('.kanban-column') || e.currentTarget;
    if (column && (column as HTMLElement).classList.contains('kanban-column')) {
        (column as HTMLElement).classList.add('drag-over');
    }
    
    return false;
}

function handleDragLeave(e: DragEvent) {
    // Find the column (could be column div or body)
    const column = (e.currentTarget as HTMLElement).closest('.kanban-column') || e.currentTarget;
    if (column && (column as HTMLElement).classList.contains('kanban-column')) {
        (column as HTMLElement).classList.remove('drag-over');
    }
}

function handleDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    
    if (!draggedTask) return;
    
    const targetColumn = (e.currentTarget as HTMLElement).closest('.kanban-column');
    if (!targetColumn) {
        console.error('Could not find target column');
        return false;
    }
    
    const targetColumnId = (targetColumn as HTMLElement).dataset.columnId;
    (targetColumn as HTMLElement).classList.remove('drag-over');
    
    if (!draggedTask || !draggedFromColumn) {
        console.warn('No dragged task or source column');
        return false;
    }
    
    if (targetColumnId === draggedFromColumn) {
        return false; // Dropped in same column
    }
    
    const taskId = draggedTask.dataset.taskId;
    if (!taskId) {
        console.error('No task ID found on dragged element');
        return false;
    }
    
    // Send move event to Streamlit
    sendMoveEvent(taskId, draggedFromColumn, targetColumnId);
    
    return false;
}

function handleDragEnd(e: DragEvent) {
    if (e.target) {
        (e.target as HTMLElement).classList.remove('dragging');
    }
    document.querySelectorAll('.kanban-column').forEach(col => {
        col.classList.remove('drag-over');
    });
    draggedTask = null;
    draggedFromColumn = null;
}

// Send events to Streamlit
function sendMoveEvent(taskId: string, fromColumn: string | null, toColumn: string | null) {
    if (!fromColumn || !toColumn) return;
    
    Streamlit.setComponentValue({
        type: 'move',
        taskId: taskId,
        fromColumn: fromColumn,
        toColumn: toColumn,
        timestamp: Date.now()
    });
}

function sendClickEvent(taskId: string) {
    Streamlit.setComponentValue({
        type: 'click',
        taskId: taskId,
        timestamp: Date.now()
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initComponent);
} else {
    initComponent();
}

// Add styles
const style = document.createElement('style');
style.textContent = `
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background-color: #000000;
        color: #ffffff;
        height: 100vh;
        overflow: hidden;
    }

    .kanban-container {
        display: flex;
        height: 100vh;
        padding: 10px;
        gap: 15px;
        overflow-x: auto;
        overflow-y: hidden;
    }

    .kanban-column {
        flex: 1;
        min-width: 280px;
        max-width: 350px;
        background-color: #1a1a1a;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        border: 1px solid #333;
    }

    .column-header {
        background-color: #2a2a2a;
        padding: 12px 16px;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        font-size: 14px;
        color: #fff;
        border-bottom: 2px solid #444;
        border-top: 3px solid #3498db;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .column-count {
        background-color: #444;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
    }

    .column-body {
        flex: 1;
        padding: 10px;
        overflow-y: auto;
        overflow-x: hidden;
        min-height: 200px;
    }

    .task-card {
        background-color: #2a2a2a;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 10px;
        cursor: move;
        transition: all 0.2s ease;
        position: relative;
    }

    .task-card:hover {
        border-color: #666;
        box-shadow: 0 2px 8px rgba(255, 255, 255, 0.1);
        transform: translateY(-2px);
        cursor: pointer;
    }

    .task-card.dragging {
        opacity: 0.5;
        transform: rotate(2deg);
    }

    .kanban-column.drag-over {
        background-color: #1a3a1a;
        border: 2px dashed #4CAF50;
    }

    .task-title {
        font-weight: 600;
        font-size: 14px;
        color: #fff;
        margin-bottom: 6px;
        word-wrap: break-word;
    }

    .task-id {
        font-size: 11px;
        color: #888;
        font-family: monospace;
        margin-bottom: 4px;
    }

    .task-meta {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 8px;
        font-size: 11px;
    }

    .task-priority {
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
    }

    .priority-high {
        background-color: #dc2626;
        color: #fff;
    }

    .priority-medium {
        background-color: #f59e0b;
        color: #fff;
    }

    .priority-low {
        background-color: #10b981;
        color: #fff;
    }

    .task-tags {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
    }

    .task-tag {
        background-color: #3a3a3a;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 10px;
        color: #ccc;
    }

    .empty-column {
        text-align: center;
        color: #666;
        padding: 40px 20px;
        font-size: 13px;
    }

    /* Scrollbar styling */
    .column-body::-webkit-scrollbar {
        width: 8px;
    }

    .column-body::-webkit-scrollbar-track {
        background: #1a1a1a;
        border-radius: 4px;
    }

    .column-body::-webkit-scrollbar-thumb {
        background: #444;
        border-radius: 4px;
    }

    .column-body::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
`;
document.head.appendChild(style);

