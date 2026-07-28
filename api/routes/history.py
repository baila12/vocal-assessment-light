"""
历史记录路由
处理历史记录查询请求
"""
from flask import Blueprint, jsonify, request

from config import config
from repositories import JsonHistoryRepository
from api.routes.rate_limit import rate_limit

history_bp = Blueprint('history', __name__)

# 初始化仓储
history_repo = JsonHistoryRepository(config.HISTORY_FILE, config.HISTORY_MAX_RECORDS)


@history_bp.route('/history', methods=['GET'])
@rate_limit(120, 60)
def get_history():
    """
    获取历史记录（支持分页）

    请求：
        GET /api/history?page=1&limit=20&date=today|week|month|all

    响应：
        {
            "success": true,
            "history": [...],
            "total": 50,
            "page": 1,
            "total_pages": 3,
            "limit": 20
        }
    """
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    date_filter = request.args.get('date', 'all')

    # 限制每页最大数量
    limit = min(limit, 50)

    # 获取分页数据
    result = history_repo.get_paginated(page=page, limit=limit, date_filter=date_filter)

    return jsonify({
        'success': True,
        'history': result['records'],
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages'],
        'limit': result['limit']
    })


@history_bp.route('/history/<record_id>', methods=['GET'])
@rate_limit(120, 60)
def get_history_detail(record_id):
    """
    获取单条历史记录详情

    响应：
        {
            "success": true,
            "record": {...}
        }
    """
    record = history_repo.get_by_id(record_id)
    if not record:
        return jsonify({
            'success': False,
            'error': '记录不存在'
        }), 404

    return jsonify({
        'success': True,
        'record': record
    })


@history_bp.route('/history/<record_id>', methods=['DELETE'])
@rate_limit(120, 60)
def delete_history(record_id):
    """
    删除历史记录

    响应：
        {
            "success": true
        }
    """
    success = history_repo.delete(record_id)
    if not success:
        return jsonify({
            'success': False,
            'error': '删除失败，记录不存在'
        }), 404

    return jsonify({
        'success': True
    })


@history_bp.route('/history/batch', methods=['DELETE'])
@rate_limit(120, 60)
def delete_history_batch():
    """
    批量删除历史记录

    请求：
        DELETE /api/history/batch
        Content-Type: application/json
        {"ids": [1, 2, 3]}

    响应：
        {
            "success": true,
            "deleted_count": 3
        }
    """
    data = request.get_json()
    if not data or 'ids' not in data:
        return jsonify({
            'success': False,
            'error': '缺少 ids 参数'
        }), 400

    ids = data['ids']
    if not isinstance(ids, list):
        return jsonify({
            'success': False,
            'error': 'ids 必须是数组'
        }), 400

    if len(ids) == 0:
        return jsonify({
            'success': False,
            'error': 'ids 不能为空'
        }), 400

    deleted_count = history_repo.delete_batch(ids)

    return jsonify({
        'success': True,
        'deleted_count': deleted_count
    })


@history_bp.route('/history/all', methods=['DELETE'])
@rate_limit(120, 60)
def delete_history_all():
    """
    删除所有历史记录

    响应：
        {
            "success": true,
            "deleted_count": 50
        }
    """
    # 获取所有记录ID
    all_records = history_repo.get_all(limit=1000)
    all_ids = [r.get('id') for r in all_records if r.get('id')]

    deleted_count = history_repo.delete_batch(all_ids)

    return jsonify({
        'success': True,
        'deleted_count': deleted_count
    })


@history_bp.route('/test-files', methods=['GET'])
@rate_limit(120, 60)
def get_test_files():
    """
    获取测试音乐文件列表

    响应：
        {
            "success": true,
            "files": [...]
        }
    """
    from pathlib import Path

    test_dir = config.PROJECT_ROOT / 'tests' / 'test_data' / 'audio'
    files = []

    if test_dir.exists():
        for f in test_dir.iterdir():
            if f.suffix.lower() in config.ALLOWED_EXTENSIONS:
                files.append({
                    'filename': f.name,
                    'filepath': str(f),
                    'size': f"{f.stat().st_size / (1024*1024):.2f}MB"
                })

    return jsonify({
        'success': True,
        'files': files
    })
