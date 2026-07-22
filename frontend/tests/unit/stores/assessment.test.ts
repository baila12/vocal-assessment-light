/**
 * assessment.store — 单元测试
 *
 * 测试: 状态初始化、模式切换、进度重置、计算属性
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAssessmentStore } from '@/stores/assessment.store'

describe('useAssessmentStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态: isAnalyzing 为 false', () => {
    const store = useAssessmentStore()
    expect(store.isAnalyzing).toBe(false)
  })

  it('初始状态: currentResult 为 null', () => {
    const store = useAssessmentStore()
    expect(store.currentResult).toBeNull()
  })

  it('初始状态: currentMode 为 quick', () => {
    const store = useAssessmentStore()
    expect(store.currentMode).toBe('quick')
  })

  it('初始状态: error 为 null', () => {
    const store = useAssessmentStore()
    expect(store.error).toBeNull()
  })

  it('setMode 修改评估模式', () => {
    const store = useAssessmentStore()
    store.setMode('professional')
    expect(store.currentMode).toBe('professional')
    store.setMode('quick')
    expect(store.currentMode).toBe('quick')
  })

  it('resetProgress 清空进度和错误', () => {
    const store = useAssessmentStore()
    store.progress = { stage: 'analyze', percent: 50, message: 'test' }
    store.error = 'some error'

    store.resetProgress()

    expect(store.progress.stage).toBe('')
    expect(store.progress.percent).toBe(0)
    expect(store.error).toBeNull()
  })

  it('reset 清空所有状态', () => {
    const store = useAssessmentStore()
    store.isAnalyzing = true
    store.error = 'test error'
    store.streamingScores = [{ progress: 0.5 }]

    store.reset()

    expect(store.isAnalyzing).toBe(false)
    expect(store.error).toBeNull()
    expect(store.currentResult).toBeNull()
    expect(store.streamingScores).toEqual([])
  })

  it('totalScore 计算属性: 从 currentResult 读取', () => {
    const store = useAssessmentStore()
    expect(store.totalScore).toBe(0)

    store.setResult({
      analysis_id: 'test-1',
      total_score: 85.5,
      scores: { pitch: 80, rhythm: 80, breath: 90, technique: 85, muscle_strength: 80, artistry: 80 },
      timbre_adjustment: 0,
      level: '优秀',
      grade: 'A',
      advice: [],
      mode: 'quick',
      is_voice: true,
      filepath: null,
      basic_info: null,
      heuristic_dimensions: [],
    })

    expect(store.totalScore).toBe(85.5)
  })

  it('heuristicDimensions 计算属性: 返回启发式维度列表', () => {
    const store = useAssessmentStore()
    store.setResult({
      analysis_id: 'test-2',
      total_score: 75,
      scores: { pitch: 70, rhythm: 70, breath: 80, technique: 75, muscle_strength: 65, artistry: 70 },
      timbre_adjustment: 2,
      level: '良好',
      grade: 'B',
      advice: [],
      mode: 'professional',
      is_voice: true,
      filepath: null,
      basic_info: null,
      heuristic_dimensions: ['muscle_strength', 'timbre'],
    })

    expect(store.heuristicDimensions).toEqual(['muscle_strength', 'timbre'])
  })

  it('level 和 grade 计算属性', () => {
    const store = useAssessmentStore()
    store.setResult({
      analysis_id: 'test-3',
      total_score: 90,
      scores: { pitch: 90, rhythm: 90, breath: 90, technique: 90, muscle_strength: 90, artistry: 90 },
      timbre_adjustment: 0,
      level: '专业级',
      grade: 'S',
      advice: [],
      mode: 'quick',
      is_voice: true,
      filepath: null,
      basic_info: null,
      heuristic_dimensions: [],
    })

    expect(store.level).toBe('专业级')
    expect(store.grade).toBe('S')
  })

  it('scores 计算属性: 返回六维分数对象', () => {
    const store = useAssessmentStore()
    const scores = {
      pitch: 82, rhythm: 78, breath: 88,
      technique: 80, muscle_strength: 75, artistry: 76,
    }
    store.setResult({
      analysis_id: 'test-4',
      total_score: 79.9,
      scores,
      timbre_adjustment: 0,
      level: '优秀',
      grade: 'A',
      advice: [],
      mode: 'quick',
      is_voice: true,
      filepath: null,
      basic_info: null,
      heuristic_dimensions: [],
    })

    expect(store.scores).toEqual(scores)
  })
})
