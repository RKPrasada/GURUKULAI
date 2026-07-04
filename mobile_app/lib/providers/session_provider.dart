import 'package:flutter/foundation.dart';
import '../models/question_model.dart';
import '../services/api_service.dart';

class SessionProvider extends ChangeNotifier {
  Map<String, dynamic>? _currentSession;
  List<Question> _questions = [];
  int _currentIndex = 0;
  List<int?> _answers = [];
  int _score = 0;
  bool _isLoading = false;
  String? _error;
  Map<String, dynamic>? _lastResult;

  List<Question> get questions => _questions;
  int get currentIndex => _currentIndex;
  List<int?> get answers => _answers;
  int get score => _score;
  bool get isLoading => _isLoading;
  String? get error => _error;
  Map<String, dynamic>? get lastResult => _lastResult;
  Question? get currentQuestion => _currentIndex < _questions.length ? _questions[_currentIndex] : null;
  String? get sessionId => _currentSession?['session_id'] as String?;
  bool get isComplete => _currentIndex >= _questions.length && _questions.isNotEmpty;

  Future<void> startDiagnostic(String studentId) async {
    _isLoading = true;
    _error = null;
    _questions = [];
    _answers = [];
    _currentIndex = 0;
    _score = 0;
    notifyListeners();
    try {
      final data = await ApiService().startDiagnostic(studentId);
      _currentSession = data;
      _questions = (data['questions'] as List)
          .map((q) => Question.fromJson(q as Map<String, dynamic>))
          .toList();
      _answers = List.filled(_questions.length, null);
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void setAnswer(int questionIndex, int answerIndex) {
    if (questionIndex < _answers.length) {
      _answers[questionIndex] = answerIndex;
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>?> submitDiagnostic(String studentId) async {
    if (sessionId == null) return null;
    _isLoading = true;
    notifyListeners();
    try {
      final filledAnswers = _answers.map((a) => a ?? 0).toList();
      final result = await ApiService().submitDiagnostic(studentId, sessionId!, filledAnswers);
      return result;
    } catch (e) {
      _error = e.toString();
      return null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> startAssessment(String studentId, {String? topic}) async {
    _isLoading = true;
    _error = null;
    _lastResult = null;
    _score = 0;
    notifyListeners();
    try {
      final data = await ApiService().startAssessment(studentId, topic: topic);
      _currentSession = data;
      _questions = [];
      _currentIndex = 0;
      if (data['first_question'] != null) {
        _questions.add(Question.fromJson(data['first_question'] as Map<String, dynamic>));
      }
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> submitAssessmentAnswer(String studentId, int answerIndex) async {
    if (currentQuestion == null || sessionId == null) return;
    _isLoading = true;
    notifyListeners();
    try {
      final result = await ApiService().submitAnswer(
          studentId, sessionId!, currentQuestion!.questionId, answerIndex);
      _lastResult = result;
      if (result['correct'] == true) _score++;
      if (result['next_question'] != null && !(result['session_complete'] as bool? ?? false)) {
        _questions.add(Question.fromJson(result['next_question'] as Map<String, dynamic>));
      }
      _currentIndex++;
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearLastResult() {
    _lastResult = null;
    notifyListeners();
  }

  void reset() {
    _currentSession = null;
    _questions = [];
    _currentIndex = 0;
    _answers = [];
    _score = 0;
    _error = null;
    _lastResult = null;
    notifyListeners();
  }
}
