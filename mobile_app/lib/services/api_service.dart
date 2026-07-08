import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  String get baseUrl => dotenv.env['API_BASE_URL'] ?? 'http://localhost:8000';

  String? _token;
  void setToken(String token) => _token = token;
  void clearToken() => _token = null;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
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

  // Health / warm-up
  Future<Map<String, dynamic>> healthCheck() => get('/health');

  // Auth
  Future<Map<String, dynamic>> demoLogin(String exam, String language, {String name = 'Demo Student'}) {
    return post('/api/student/demo', {
      'exam_target': exam,
      'preferred_language': language,
      'name': name,
    });
  }

  Future<Map<String, dynamic>> login(String username, String password) {
    return post('/api/auth/login', {'username': username, 'password': password});
  }

  Future<Map<String, dynamic>> forgotPassword(String email) {
    return post('/api/auth/forgot-password?email=${Uri.encodeQueryComponent(email)}', {});
  }

  Future<Map<String, dynamic>> resetPassword({
    required String userId,
    required String resetToken,
    required String newPassword,
    required String confirmPassword,
  }) {
    return post('/api/auth/reset-password', {
      'user_id': userId,
      'reset_token': resetToken,
      'new_password': newPassword,
      'confirm_password': confirmPassword,
    });
  }

  Future<Map<String, dynamic>> register({
    required String username,
    required String email,
    required String password,
    required String confirmPassword,
    required String fullName,
    required String examTarget,
    String language = 'en',
    String trade = '',
    String engineeringDiscipline = '',
  }) {
    return post('/api/auth/register', {
      'username': username,
      'email': email,
      'password': password,
      'confirm_password': confirmPassword,
      'full_name': fullName,
      'exam_target': examTarget,
      'preferred_language': language,
      'trade': trade,
      'engineering_discipline': engineeringDiscipline,
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

  // Diagnostic — long timeout because the server generates ~100 questions via LLM
  Future<Map<String, dynamic>> startDiagnostic(String studentId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/session/diagnostic/start'),
      headers: _headers,
      body: jsonEncode({'student_id': studentId, 'paper_id': 'p1'}),
    ).timeout(const Duration(seconds: 120));
    return _parseResponse(response);
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

  Future<Map<String, dynamic>> getStudyNotes(String topic) {
    return post('/api/session/content', {'message': topic});
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

  // ── Mock Test ─────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getMockStatus(String examKey) =>
      get('/api/mock/status/$examKey');

  Future<Map<String, dynamic>> getMockPaper(String examKey) =>
      get('/api/mock/paper/$examKey');

  Future<Map<String, dynamic>> startMockSession(String examKey) =>
      post('/api/mock/session/start', {'exam_key': examKey});

  Future<Map<String, dynamic>> autosaveMock(
      String sessionId, List<int> answers, List<int> flagged) =>
      _put('/api/mock/session/$sessionId', {'answers': answers, 'flagged': flagged});

  Future<Map<String, dynamic>> submitMock(
      String sessionId, List<int> answers, List<int> flagged) =>
      post('/api/mock/session/$sessionId/submit', {'answers': answers, 'flagged': flagged});

  Future<Map<String, dynamic>> getMockSession(String sessionId) =>
      get('/api/mock/session/$sessionId');

  Future<Map<String, dynamic>> getMockHistory() => get('/api/mock/history');

  // ── NAGA / Mentor ─────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> postQuestionToNaga({
    required String studentId,
    required String content,
    required String subject,
    String? topic,
  }) =>
      post('/api/mentor/questions', {
        'content': content,
        'subject': subject,
        'topic': topic ?? subject,
      });

  Future<Map<String, dynamic>> getNagaQuestions({String? studentId}) =>
      get('/api/mentor/questions${studentId != null ? '?student_id=$studentId' : ''}');

  Future<Map<String, dynamic>> getNagaNotifications() =>
      get('/api/mentor/notifications');

  Future<Map<String, dynamic>> markNotificationRead(String notificationId) =>
      post('/api/mentor/notifications/$notificationId/read', {});

  Future<Map<String, dynamic>> requestMeeting(
      String studentId, String topic, String message) =>
      post('/api/mentor/meeting-requests', {
        'student_id': studentId,
        'topic': topic,
        'message': message,
      });

  Future<Map<String, dynamic>> getMeetingRequests() =>
      get('/api/mentor/meeting-requests');

  Future<Map<String, dynamic>> getNagaClasses() => get('/api/mentor/classes');

  Future<Map<String, dynamic>> rsvpClass(String classId, bool attending) =>
      post('/api/mentor/classes/$classId/rsvp', {'attending': attending});

  // ── Progress / Dabbu ─────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getFullProgress() => get('/api/progress');

  Future<Map<String, dynamic>> takeSnapshot() =>
      post('/api/progress/snapshot', {});

  Future<Map<String, dynamic>> triggerDabbuAnalysis() =>
      post('/api/progress/dabbu-analyze', {});

  Future<Map<String, dynamic>> getInterventions() =>
      get('/api/progress/interventions');

  Future<Map<String, dynamic>> getDabbuStudyPlan() =>
      get('/api/dabbu/study-plan');

  Future<Map<String, dynamic>> getProposedStudyPlan() =>
      get('/api/dabbu/study-plan/proposed');

  Future<Map<String, dynamic>> generateStudyPlan({String? examDate}) =>
      post('/api/dabbu/study-plan', {if (examDate != null) 'exam_date': examDate});

  Future<Map<String, dynamic>> getDueReviews() =>
      get('/api/progress/due-reviews');

  // ── Internal helpers ──────────────────────────────────────────────────────

  Future<Map<String, dynamic>> _put(String endpoint, Map<String, dynamic> body) =>
      put(endpoint, body);
}

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException($statusCode): $message';
}
