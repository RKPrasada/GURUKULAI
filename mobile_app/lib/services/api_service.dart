import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  String get baseUrl => dotenv.env['API_BASE_URL'] ?? 'http://localhost:8000';

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  Future<Map<String, dynamic>> get(String endpoint) async {
    final response = await http.get(
      Uri.parse('$baseUrl$endpoint'),
      headers: _headers,
    ).timeout(const Duration(seconds: 30));
    return _parseResponse(response);
  }

  Future<Map<String, dynamic>> post(String endpoint, Map<String, dynamic> body) async {
    final response = await http.post(
      Uri.parse('$baseUrl$endpoint'),
      headers: _headers,
      body: jsonEncode(body),
    ).timeout(const Duration(seconds: 60));
    return _parseResponse(response);
  }

  Future<Map<String, dynamic>> put(String endpoint, Map<String, dynamic> body) async {
    final response = await http.put(
      Uri.parse('$baseUrl$endpoint'),
      headers: _headers,
      body: jsonEncode(body),
    ).timeout(const Duration(seconds: 30));
    return _parseResponse(response);
  }

  Map<String, dynamic> _parseResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw ApiException(response.statusCode, response.body);
  }

  // Auth
  Future<Map<String, dynamic>> demoLogin(String exam, String language, {String name = 'Demo Student'}) {
    return post('/api/student/demo', {
      'exam_target': exam,
      'preferred_language': language,
      'name': name,
    });
  }

  // Student
  Future<Map<String, dynamic>> getStudent(String studentId) => get('/api/student/$studentId');

  Future<Map<String, dynamic>> updateExam(String studentId, String exam, String language) {
    return put('/api/student/$studentId/exam', {
      'exam_target': exam,
      'preferred_language': language,
    });
  }

  // Diagnostic
  Future<Map<String, dynamic>> startDiagnostic(String studentId) {
    return get('/api/session/diagnostic/start?student_id=$studentId');
  }

  Future<Map<String, dynamic>> submitDiagnostic(
      String studentId, String sessionId, List<int> answers) {
    return post('/api/session/diagnostic/submit', {
      'student_id': studentId,
      'session_id': sessionId,
      'answers': answers,
    });
  }

  // Chat / Study
  Future<Map<String, dynamic>> sendMessage(String studentId, String message) {
    return post('/api/session/chat', {'student_id': studentId, 'message': message});
  }

  // Assessment
  Future<Map<String, dynamic>> startAssessment(String studentId, {String? topic}) {
    return post('/api/session/assessment/start', {
      'student_id': studentId,
      if (topic != null) 'topic': topic,
    });
  }

  Future<Map<String, dynamic>> submitAnswer(
      String studentId, String sessionId, String questionId, int answerIndex) {
    return post('/api/session/assessment/answer', {
      'student_id': studentId,
      'session_id': sessionId,
      'question_id': questionId,
      'answer_index': answerIndex,
    });
  }

  // Progress
  Future<Map<String, dynamic>> getStudyPlan(String studentId) => get('/api/progress/$studentId/plan');

  Future<Map<String, dynamic>> createSchedule(String studentId) {
    return post('/api/progress/$studentId/schedule', {});
  }

  Future<Map<String, dynamic>> sendDigest(String studentId, String email, String name) {
    return post('/api/progress/$studentId/digest', {
      'student_id': studentId,
      'email': email,
      'name': name,
    });
  }

  Future<Map<String, dynamic>> getProgressSummary(String studentId) =>
    get('/api/student/$studentId/progress');

  // Vibe Diff confirmation
  Future<Map<String, dynamic>> confirmAction(
      String studentId, String route, String token) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/progress/$studentId/$route/execute?token=$token'),
      headers: _headers,
    ).timeout(const Duration(seconds: 30));
    return _parseResponse(response);
  }

  // Pending actions list
  Future<Map<String, dynamic>> getPendingActions(String studentId) =>
    get('/api/session/pending-actions/$studentId');
}

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException($statusCode): $message';
}
