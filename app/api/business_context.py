"""
Business Context API routes - Visual resource mapping
"""
from flask import Blueprint, jsonify, request, session
from app.core.database import db
from app.core.models.business_board import BusinessBoard
from app.core.models.board_resource import BoardResource
from app.core.models.board_group import BoardGroup
from app.core.models.resource import Resource
from app.core.models.provider import CloudProvider
from app.api.auth import validate_session, check_demo_user_write_access
from app.core.organization_context import get_current_organization_id, get_user_role_in_organization

business_context_bp = Blueprint('business_context', __name__)


def require_editor_or_owner():
    """Helper to check if user is editor or owner in current organization
    
    Returns:
        tuple: (user_id, org_id) if authorized, or (None, error_response) if not
    """
    user_id = session.get('user', {}).get('db_id')
    if not user_id:
        return None, jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    org_id = get_current_organization_id()
    if not org_id:
        return None, jsonify({'success': False, 'error': 'No active organization'}), 400
    
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return None, jsonify({'success': False, 'error': 'Только редакторы и владельцы могут выполнять это действие'}), 403
    
    return user_id, org_id


# ============================================================================
# BOARD MANAGEMENT
# ============================================================================

@business_context_bp.route('/boards', methods=['GET'])
@validate_session
def list_boards():
    """Get all boards for current organization (viewers see all boards in org)"""
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Filter boards by organization only - viewers should see all boards in the organization
    boards = BusinessBoard.query.filter_by(organization_id=org_id).order_by(BusinessBoard.updated_at.desc()).all()
    
    return jsonify({
        'success': True,
        'boards': [board.to_dict() for board in boards],
        'count': len(boards)
    })


@business_context_bp.route('/boards/<int:board_id>', methods=['GET'])
@validate_session
def get_board(board_id):
    """Get specific board with full canvas state - viewers can view all boards in org"""
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Filter by organization only - viewers should be able to view all boards in the organization
    board = BusinessBoard.query.filter_by(id=board_id, organization_id=org_id).first()
    
    if not board:
        return jsonify({'success': False, 'error': 'Board not found'}), 404
    
    # Get board with canvas state
    board_data = board.to_dict(include_canvas=True)
    
    # Include resources and groups
    board_data['resources'] = [br.to_dict(include_resource=True) for br in board.resources.all()]
    board_data['groups'] = [g.to_dict(include_resources=False) for g in board.groups.all()]
    
    return jsonify({
        'success': True,
        'board': board_data
    })


@business_context_bp.route('/boards', methods=['POST'])
@validate_session
def create_board():
    """Create new board - only editors and owners can create"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can create boards
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут создавать доски'}), 403
    
    data = request.get_json()
    name = data.get('name', 'Untitled Board')
    
    # Create board
    board = BusinessBoard(
        user_id=user_id,
        organization_id=org_id,
        name=name,
        is_default=False,
        canvas_state=None,
        viewport={'zoom': 1.0, 'pan_x': 0, 'pan_y': 0}
    )
    
    board.save()
    
    # If this is the user's first board in this organization, make it default
    if BusinessBoard.query.filter_by(user_id=user_id, organization_id=org_id).count() == 1:
        board.is_default = True
        db.session.commit()
    
    return jsonify({
        'success': True,
        'board': board.to_dict(include_canvas=True)
    }), 201


@business_context_bp.route('/boards/<int:board_id>', methods=['PUT'])
@validate_session
def update_board(board_id):
    """Update board (name, canvas_state, viewport) - only editors and owners can edit"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can edit boards
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут редактировать доски'}), 403
    
    board = BusinessBoard.query.filter_by(id=board_id, organization_id=org_id).first()
    
    if not board:
        return jsonify({'success': False, 'error': 'Board not found'}), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if 'name' in data:
        board.name = data['name']
    
    if 'canvas_state' in data:
        board.canvas_state = data['canvas_state']
    
    if 'viewport' in data:
        board.viewport = data['viewport']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'board': board.to_dict(include_canvas=True)
    })


@business_context_bp.route('/boards/<int:board_id>', methods=['DELETE'])
@validate_session
def delete_board(board_id):
    """Delete board"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can delete boards
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут удалять доски'}), 403
    
    board = BusinessBoard.query.filter_by(id=board_id, organization_id=org_id).first()
    
    if not board:
        return jsonify({'success': False, 'error': 'Board not found'}), 404
    
    board.delete()
    
    return jsonify({
        'success': True,
        'message': 'Board deleted successfully'
    })


@business_context_bp.route('/boards/<int:board_id>/default', methods=['PUT'])
@validate_session
def set_default_board(board_id):
    """Set board as default"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can set default board
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут устанавливать доску по умолчанию'}), 403
    
    board = BusinessBoard.set_default_board(user_id, board_id, org_id)
    
    if not board:
        return jsonify({'success': False, 'error': 'Board not found'}), 404
    
    return jsonify({
        'success': True,
        'board': board.to_dict()
    })


# ============================================================================
# RESOURCE MANAGEMENT
# ============================================================================

@business_context_bp.route('/available-resources', methods=['GET'])
@validate_session
def get_available_resources():
    """Get all organization resources with placement status for a specific board"""
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Get board_id from query parameter (optional for backward compatibility)
    board_id = request.args.get('board_id', type=int)
    
    # Get all resources in the organization (not just user's own)
    # Editors and viewers should see all resources in the organization
    resources = Resource.query.filter(
        Resource.organization_id == org_id,
        Resource.is_active == True
    ).all()
    
    # Get placed resource IDs for the specific board (or all boards if no board_id)
    placed_resource_ids = set()
    if board_id:
        # Check placement only for the specific board
        placed_resources = BoardResource.query.filter(
            BoardResource.board_id == board_id
        ).all()
        placed_resource_ids = {br.resource_id for br in placed_resources}
    else:
        # Legacy behavior: check all boards
        # Get current organization ID
        org_id = get_current_organization_id()
        if not org_id:
            return jsonify({'success': False, 'error': 'No active organization'}), 400
        
        # Get all boards in the organization (not just user's own)
        board_ids = [b.id for b in BusinessBoard.query.filter_by(organization_id=org_id).all()]
        if board_ids:
            placed_resources = BoardResource.query.filter(
                BoardResource.board_id.in_(board_ids)
            ).all()
            placed_resource_ids = {br.resource_id for br in placed_resources}
    
    # Build response with placement status
    resources_data = []
    for r in resources:
        resource_dict = {
            'id': r.id,
            'name': r.resource_name,
            'type': r.resource_type,
            'service': r.service_name,
            'ip': r.external_ip,
            'region': r.region,
            'status': r.status,
            'provider_id': r.provider_id,
            'daily_cost': float(r.daily_cost) if r.daily_cost else 0.0,
            'currency': r.currency,
            'notes': r.notes,
            'has_notes': bool(r.notes),
            'is_placed': r.id in placed_resource_ids
        }
        resources_data.append(resource_dict)
    
    # Group by provider
    grouped = {}
    for r in resources_data:
        provider_id = r['provider_id']
        if provider_id not in grouped:
            provider = CloudProvider.query.get(provider_id)
            grouped[provider_id] = {
                'provider_id': provider_id,
                'provider_name': provider.connection_name if provider else 'Unknown',
                'provider_type': provider.provider_type if provider else 'unknown',
                'resources': []
            }
        grouped[provider_id]['resources'].append(r)
    
    return jsonify({
        'success': True,
        'resources': list(grouped.values()),
        'total_count': len(resources),
        'unplaced_count': len([r for r in resources_data if not r['is_placed']])
    })


@business_context_bp.route('/boards/<int:board_id>/resources', methods=['POST'])
@validate_session
def place_resource_on_board(board_id):
    """Place resource on board"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can place resources
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут размещать ресурсы на досках'}), 403
    
    # Verify board belongs to organization
    board = BusinessBoard.query.filter_by(id=board_id, organization_id=org_id).first()
    if not board:
        return jsonify({'success': False, 'error': 'Board not found'}), 404
    
    data = request.get_json()
    resource_id = data.get('resource_id')
    position_x = data.get('position_x', 0)
    position_y = data.get('position_y', 0)
    group_id = data.get('group_id')
    
    if not resource_id:
        return jsonify({'success': False, 'error': 'resource_id is required'}), 400
    
    # Verify resource exists and belongs to organization
    resource = Resource.query.join(
        CloudProvider, Resource.provider_id == CloudProvider.id
    ).filter(
        Resource.id == resource_id,
        Resource.organization_id == org_id
    ).first()
    
    if not resource:
        return jsonify({'success': False, 'error': 'Resource not found'}), 404
    
    # Note: We allow multiple placements (clones) of the same resource
    # Each placement is tracked separately with its own board_resource_id
    
    # Verify group if provided
    if group_id:
        group = BoardGroup.query.filter_by(id=group_id, board_id=board_id).first()
        if not group:
            return jsonify({'success': False, 'error': 'Group not found on this board'}), 404
    
    # Create board resource
    board_resource = BoardResource(
        board_id=board_id,
        resource_id=resource_id,
        position_x=position_x,
        position_y=position_y,
        group_id=group_id,
        notes=None
    )
    
    board_resource.save()
    print(f'📦 Resource placed: resource_id={resource_id}, group_id={group_id}')
    
    # Update group cost if assigned to group
    if group_id:
        group = BoardGroup.query.get(group_id)
        if group:
            group.calculate_cost()
    
    return jsonify({
        'success': True,
        'board_resource': board_resource.to_dict(include_resource=True)
    }), 201


@business_context_bp.route('/board-resources/<int:board_resource_id>', methods=['PUT'])
@validate_session
def update_board_resource(board_resource_id):
    """Update board resource (position, group, notes)"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get board resource and verify ownership
    board_resource = BoardResource.query.join(
        BusinessBoard, BoardResource.board_id == BusinessBoard.id
    ).filter(
        BoardResource.id == board_resource_id,
        BusinessBoard.user_id == user_id
    ).first()
    
    if not board_resource:
        return jsonify({'success': False, 'error': 'Board resource not found'}), 404
    
    data = request.get_json()
    
    old_group_id = board_resource.group_id
    
    # Update fields if provided
    if 'position_x' in data:
        board_resource.position_x = data['position_x']
    
    if 'position_y' in data:
        board_resource.position_y = data['position_y']
    
    if 'group_id' in data:
        board_resource.group_id = data['group_id']
    
    if 'notes' in data:
        board_resource.notes = data['notes']
    
    db.session.commit()
    
    # Update group costs if group changed
    try:
        if old_group_id != board_resource.group_id:
            if old_group_id:
                old_group = BoardGroup.query.get(old_group_id)
                if old_group:
                    old_group.calculate_cost()
            
            if board_resource.group_id:
                new_group = BoardGroup.query.get(board_resource.group_id)
                if new_group:
                    new_group.calculate_cost()
    except Exception as e:
        print(f"❌ Error calculating group cost: {e}")
        import traceback
        traceback.print_exc()
        # Don't fail the whole request if cost calc fails
    
    return jsonify({
        'success': True,
        'board_resource': board_resource.to_dict(include_resource=True)
    })


@business_context_bp.route('/board-resources/<int:board_resource_id>', methods=['DELETE'])
@validate_session
def remove_resource_from_board(board_resource_id):
    """Remove resource from board - only editors and owners can remove"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can remove resources
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут удалять ресурсы с досок'}), 403
    
    # Get board resource and verify it belongs to organization
    board_resource = BoardResource.query.join(
        BusinessBoard, BoardResource.board_id == BusinessBoard.id
    ).filter(
        BoardResource.id == board_resource_id,
        BusinessBoard.organization_id == org_id
    ).first()
    
    if not board_resource:
        return jsonify({'success': False, 'error': 'Board resource not found'}), 404
    
    group_id = board_resource.group_id
    board_resource.delete()
    
    # Update group cost if was in a group
    if group_id:
        group = BoardGroup.query.get(group_id)
        if group:
            group.calculate_cost()
    
    return jsonify({
        'success': True,
        'message': 'Resource removed from board'
    })


@business_context_bp.route('/board-resources/<int:board_resource_id>/notes', methods=['PUT'])
@validate_session
def update_resource_notes(board_resource_id):
    """Update resource notes - only editors and owners can update"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can update notes
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут редактировать заметки'}), 403
    
    # Get board resource and verify it belongs to organization
    board_resource = BoardResource.query.join(
        BusinessBoard, BoardResource.board_id == BusinessBoard.id
    ).filter(
        BoardResource.id == board_resource_id,
        BusinessBoard.organization_id == org_id
    ).first()
    
    if not board_resource:
        return jsonify({'success': False, 'error': 'Board resource not found'}), 404
    
    data = request.get_json()
    notes = data.get('notes', '')
    
    board_resource.notes = notes if notes else None
    db.session.commit()
    
    return jsonify({
        'success': True,
        'notes': board_resource.notes,
        'has_notes': bool(board_resource.notes)
    })


@business_context_bp.route('/resources/<int:resource_id>/notes', methods=['PUT'])
@validate_session
def update_resource_system_notes(resource_id):
    """Update system-wide resource notes (not board-specific) - only editors and owners"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can update system notes
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут редактировать системные заметки'}), 403
    
    # Get resource and verify it belongs to organization
    resource = Resource.query.filter_by(
        id=resource_id,
        organization_id=org_id
    ).first()
    
    if not resource:
        return jsonify({'success': False, 'error': 'Resource not found'}), 404
    
    data = request.get_json()
    notes = data.get('notes', '')
    
    resource.notes = notes if notes else None
    db.session.commit()
    
    return jsonify({
        'success': True,
        'notes': resource.notes,
        'has_notes': bool(resource.notes)
    })


# ============================================================================
# GROUP MANAGEMENT
# ============================================================================

@business_context_bp.route('/boards/<int:board_id>/groups', methods=['POST'])
@validate_session
def create_group(board_id):
    """Create group on board"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can create groups
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут создавать группы'}), 403
    
    # Verify board belongs to organization
    board = BusinessBoard.query.filter_by(id=board_id, organization_id=org_id).first()
    if not board:
        return jsonify({'success': False, 'error': 'Board not found'}), 404
    
    data = request.get_json()
    
    required_fields = ['name', 'fabric_id', 'position_x', 'position_y', 'width', 'height']
    for field in required_fields:
        if field not in data:
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
    
    # Create group
    group = BoardGroup(
        board_id=board_id,
        name=data['name'],
        fabric_id=data['fabric_id'],
        position_x=data['position_x'],
        position_y=data['position_y'],
        width=data['width'],
        height=data['height'],
        color=data.get('color', '#3B82F6'),
        calculated_cost=0.0
    )
    
    group.save()
    
    return jsonify({
        'success': True,
        'group': group.to_dict()
    }), 201


@business_context_bp.route('/groups/<int:group_id>', methods=['PUT'])
@validate_session
def update_group(group_id):
    """Update group properties"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can update groups
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут редактировать группы'}), 403
    
    # Get group and verify it belongs to organization
    group = BoardGroup.query.join(
        BusinessBoard, BoardGroup.board_id == BusinessBoard.id
    ).filter(
        BoardGroup.id == group_id,
        BusinessBoard.organization_id == org_id
    ).first()
    
    if not group:
        return jsonify({'success': False, 'error': 'Group not found'}), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if 'name' in data:
        group.name = data['name']
    
    if 'position_x' in data:
        group.position_x = data['position_x']
    
    if 'position_y' in data:
        group.position_y = data['position_y']
    
    if 'width' in data:
        group.width = data['width']
    
    if 'height' in data:
        group.height = data['height']
    
    if 'color' in data:
        group.color = data['color']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'group': group.to_dict()
    })


@business_context_bp.route('/groups/<int:group_id>', methods=['DELETE'])
@validate_session
def delete_group(group_id):
    """Delete group (resources remain on board)"""
    # Check if demo user
    demo_check = check_demo_user_write_access()
    if demo_check:
        return demo_check
    
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get current organization ID
    org_id = get_current_organization_id()
    if not org_id:
        return jsonify({'success': False, 'error': 'No active organization'}), 400
    
    # Check user role - only editors and owners can delete groups
    user_role = get_user_role_in_organization(user_id, org_id)
    if user_role not in ['editor', 'owner']:
        return jsonify({'success': False, 'error': 'Только редакторы и владельцы могут удалять группы'}), 403
    
    # Get group and verify it belongs to organization
    group = BoardGroup.query.join(
        BusinessBoard, BoardGroup.board_id == BusinessBoard.id
    ).filter(
        BoardGroup.id == group_id,
        BusinessBoard.organization_id == org_id
    ).first()
    
    if not group:
        return jsonify({'success': False, 'error': 'Group not found'}), 404
    
    group.delete()
    
    return jsonify({
        'success': True,
        'message': 'Group deleted successfully'
    })


@business_context_bp.route('/groups/<int:group_id>/cost', methods=['GET'])
@validate_session
def get_group_cost(group_id):
    """Calculate and return group cost"""
    user_id = session.get('user', {}).get('db_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get group and verify ownership
    group = BoardGroup.query.join(
        BusinessBoard, BoardGroup.board_id == BusinessBoard.id
    ).filter(
        BoardGroup.id == group_id,
        BusinessBoard.user_id == user_id
    ).first()
    
    if not group:
        return jsonify({'success': False, 'error': 'Group not found'}), 404
    
    print(f"🔍 get_group_cost: group {group_id} found, calculating cost...")
    
    try:
        print(f"🔍 Calling calculate_cost() for group {group_id}")
        cost = group.calculate_cost()
        print(f"✅ Cost calculated: {cost}")
        
        resource_count = group.resources.count()
        print(f"✅ Resource count: {resource_count}")
        
        return jsonify({
            'success': True,
            'group_id': group_id,
            'calculated_cost': cost,
            'resource_count': resource_count
        })
    except Exception as e:
        print(f"❌ Error in get_group_cost: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error calculating cost: {str(e)}'
        }), 500

