import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';

class NagaScreen extends StatefulWidget {
  const NagaScreen({super.key});

  @override
  State<NagaScreen> createState() => _NagaScreenState();
}

class _NagaScreenState extends State<NagaScreen> with SingleTickerProviderStateMixin {
  late TabController _tabs;
  List<Map<String, dynamic>> _questions = [];
  List<Map<String, dynamic>> _classes = [];
  List<Map<String, dynamic>> _notifications = [];
  bool _loading = false;
  int _unread = 0;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        ApiService().getNagaQuestions().catchError((_) => <String, dynamic>{}),
        ApiService().getNagaClasses().catchError((_) => <String, dynamic>{}),
        ApiService().getNagaNotifications().catchError((_) => <String, dynamic>{}),
      ]);
      setState(() {
        _questions = ((results[0]['questions'] ?? results[0]['items'] ?? []) as List)
            .cast<Map<String, dynamic>>();
        _classes = ((results[1]['classes'] ?? results[1]['items'] ?? []) as List)
            .cast<Map<String, dynamic>>();
        final notifs = ((results[2]['notifications'] ?? results[2]['items'] ?? []) as List)
            .cast<Map<String, dynamic>>();
        _notifications = notifs;
        _unread = notifs.where((n) => n['read'] == false).length;
      });
    } catch (_) {
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = context.watch<AuthProvider>().student?.preferredLanguage ?? 'en';
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const CircleAvatar(
              radius: 16,
              backgroundColor: AppTheme.primary,
              child: Text('N', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(width: 8),
            Text(lang == 'hi' ? 'NAGA गुरु' : 'NAGA Mentor'),
          ],
        ),
        actions: [
          if (_unread > 0)
            Stack(
              children: [
                IconButton(
                  icon: const Icon(Icons.notifications_outlined),
                  onPressed: () => _tabs.animateTo(2),
                ),
                Positioned(
                  right: 8, top: 8,
                  child: CircleAvatar(
                    radius: 8,
                    backgroundColor: Colors.red,
                    child: Text('$_unread', style: const TextStyle(color: Colors.white, fontSize: 10)),
                  ),
                ),
              ],
            ),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
        bottom: TabBar(
          controller: _tabs,
          tabs: [
            Tab(text: lang == 'hi' ? 'प्रश्न' : 'Questions'),
            Tab(text: lang == 'hi' ? 'कक्षाएं' : 'Classes'),
            Tab(text: lang == 'hi' ? 'सूचनाएं' : 'Notices'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabs,
              children: [
                _QuestionsTab(questions: _questions, onRefresh: _load, lang: lang),
                _ClassesTab(classes: _classes, lang: lang),
                _NotificationsTab(notifications: _notifications, onRefresh: _load, lang: lang),
              ],
            ),
      floatingActionButton: _tabs.index == 0
          ? FloatingActionButton.extended(
              onPressed: () => _showAskSheet(context, lang),
              icon: const Icon(Icons.add),
              label: Text(lang == 'hi' ? 'NAGA से पूछें' : 'Ask NAGA'),
            )
          : null,
    );
  }

  void _showAskSheet(BuildContext context, String lang) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusLarge)),
      ),
      builder: (_) => _AskNagaSheet(onSubmit: _load, lang: lang),
    );
  }
}

// ── Questions Tab ─────────────────────────────────────────────────────────────

class _QuestionsTab extends StatelessWidget {
  final List<Map<String, dynamic>> questions;
  final VoidCallback onRefresh;
  final String lang;
  const _QuestionsTab({required this.questions, required this.onRefresh, required this.lang});

  @override
  Widget build(BuildContext context) {
    if (questions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('🙋', style: TextStyle(fontSize: 48)),
            const SizedBox(height: 12),
            Text(lang == 'hi' ? 'NAGA से कुछ पूछें!' : 'Ask NAGA your first question!',
                style: const TextStyle(fontSize: 16, color: Colors.grey)),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: () async => onRefresh(),
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: questions.length,
        itemBuilder: (_, i) => _QuestionCard(q: questions[i], lang: lang),
      ),
    );
  }
}

class _QuestionCard extends StatelessWidget {
  final Map<String, dynamic> q;
  final String lang;
  const _QuestionCard({required this.q, required this.lang});

  @override
  Widget build(BuildContext context) {
    final status = q['status'] as String? ?? 'pending';
    final answer = q['answer'] as String?;
    final statusColor = status == 'answered' ? Colors.green : status == 'approved' ? AppTheme.primary : Colors.orange;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(q['subject'] as String? ?? '',
                      style: const TextStyle(fontSize: 11, color: Colors.grey)),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(status.toUpperCase(),
                      style: TextStyle(fontSize: 10, color: statusColor, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(q['question'] as String? ?? '', style: const TextStyle(fontSize: 14, height: 1.4)),
            if (answer != null) ...[
              const Divider(height: 20),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CircleAvatar(
                    radius: 12,
                    backgroundColor: AppTheme.primary,
                    child: Text('N', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(answer,
                        style: const TextStyle(fontSize: 13, color: Colors.black87, height: 1.4)),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ── Classes Tab ───────────────────────────────────────────────────────────────

class _ClassesTab extends StatelessWidget {
  final List<Map<String, dynamic>> classes;
  final String lang;
  const _ClassesTab({required this.classes, required this.lang});

  @override
  Widget build(BuildContext context) {
    if (classes.isEmpty) {
      return Center(
        child: Text(lang == 'hi' ? 'कोई कक्षा निर्धारित नहीं है' : 'No classes scheduled yet',
            style: const TextStyle(color: Colors.grey)),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: classes.length,
      itemBuilder: (_, i) => _ClassCard(c: classes[i], lang: lang),
    );
  }
}

class _ClassCard extends StatelessWidget {
  final Map<String, dynamic> c;
  final String lang;
  const _ClassCard({required this.c, required this.lang});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('📅', style: TextStyle(fontSize: 20)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(c['title'] as String? ?? 'Class',
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                ),
              ],
            ),
            if (c['description'] != null) ...[
              const SizedBox(height: 4),
              Text(c['description'] as String, style: const TextStyle(color: Colors.grey, fontSize: 13)),
            ],
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(Icons.schedule, size: 14, color: Colors.grey.shade500),
                const SizedBox(width: 4),
                Text(c['scheduled_time'] as String? ?? '', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                const Spacer(),
                _SmallOutlinedButton(
                  label: lang == 'hi' ? 'शामिल हों' : 'RSVP',
                  onPressed: () async {
                    try {
                      await ApiService().rsvpClass(c['class_id'] as String, true);
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('✅ RSVP confirmed!')));
                    } catch (e) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                    }
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ── Notifications Tab ─────────────────────────────────────────────────────────

class _NotificationsTab extends StatelessWidget {
  final List<Map<String, dynamic>> notifications;
  final VoidCallback onRefresh;
  final String lang;
  const _NotificationsTab({required this.notifications, required this.onRefresh, required this.lang});

  @override
  Widget build(BuildContext context) {
    if (notifications.isEmpty) {
      return Center(
        child: Text(lang == 'hi' ? 'कोई सूचना नहीं' : 'No notifications yet',
            style: const TextStyle(color: Colors.grey)),
      );
    }
    return RefreshIndicator(
      onRefresh: () async => onRefresh(),
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: notifications.length,
        itemBuilder: (_, i) {
          final n = notifications[i];
          final read = n['read'] as bool? ?? true;
          return Card(
            color: read ? null : AppTheme.primary.withOpacity(0.05),
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: Text(
                n['type'] == 'dabbu_intervention' ? '🤖' :
                n['type'] == 'naga_answer' ? '👨‍🏫' : '🔔',
                style: const TextStyle(fontSize: 24),
              ),
              title: Text(n['title'] as String? ?? 'Notification',
                  style: TextStyle(fontWeight: read ? FontWeight.normal : FontWeight.bold)),
              subtitle: Text(n['body'] as String? ?? n['message'] as String? ?? '',
                  maxLines: 2, overflow: TextOverflow.ellipsis),
              trailing: read ? null : const CircleAvatar(radius: 4, backgroundColor: AppTheme.primary),
              onTap: () async {
                if (!read) {
                  try {
                    await ApiService().markNotificationRead(n['notification_id'] as String);
                    onRefresh();
                  } catch (_) {}
                }
              },
            ),
          );
        },
      ),
    );
  }
}

// ── Ask NAGA Sheet ────────────────────────────────────────────────────────────

class _AskNagaSheet extends StatefulWidget {
  final VoidCallback onSubmit;
  final String lang;
  const _AskNagaSheet({required this.onSubmit, required this.lang});

  @override
  State<_AskNagaSheet> createState() => _AskNagaSheetState();
}

class _AskNagaSheetState extends State<_AskNagaSheet> {
  final _questionCtrl = TextEditingController();
  String _subject = 'General';
  bool _sending = false;

  final _subjects = ['General', 'Mathematics', 'Physics', 'Chemistry', 'Biology',
    'English', 'Reasoning', 'General Knowledge', 'Current Affairs'];

  @override
  void dispose() {
    _questionCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_questionCtrl.text.trim().isEmpty) return;
    setState(() => _sending = true);
    final student = context.read<AuthProvider>().student!;
    try {
      await ApiService().postQuestionToNaga(
        studentId: student.studentId,
        question: _questionCtrl.text.trim(),
        subject: _subject,
      );
      if (mounted) Navigator.pop(context);
      widget.onSubmit();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(widget.lang == 'hi'
                ? '✅ NAGA को आपका प्रश्न भेजा गया!'
                : '✅ Question sent to NAGA!'),
            backgroundColor: AppTheme.successColor,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        // Extract the detail message from ApiException JSON body
        String msg;
        if (e is ApiException) {
          try {
            final body = jsonDecode(e.message) as Map<String, dynamic>;
            msg = body['detail'] as String? ?? e.message;
          } catch (_) {
            msg = e.message;
          }
        } else {
          msg = e.toString();
        }
        final isGuardrail = e is ApiException && e.statusCode == 400;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Row(
            children: [
              if (isGuardrail) ...[
                const Icon(Icons.shield_outlined, color: Colors.white, size: 18),
                const SizedBox(width: 8),
              ],
              Expanded(child: Text(msg)),
            ],
          ),
          backgroundColor: isGuardrail ? Colors.amber.shade700 : Colors.red.shade700,
        ));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final lang = widget.lang;
    return Padding(
      padding: EdgeInsets.only(
        left: 24, right: 24, top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(lang == 'hi' ? 'NAGA से प्रश्न पूछें' : 'Ask NAGA a Question',
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(lang == 'hi' ? 'NAGA आपके प्रश्न की समीक्षा करेंगे और जवाब देंगे'
              : 'NAGA will review and answer your question',
              style: const TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _subject,
            decoration: InputDecoration(
              labelText: lang == 'hi' ? 'विषय' : 'Subject',
              prefixIcon: const Icon(Icons.category_outlined),
            ),
            items: _subjects.map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
            onChanged: (v) => setState(() => _subject = v!),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _questionCtrl,
            maxLines: 4,
            decoration: InputDecoration(
              labelText: lang == 'hi' ? 'आपका प्रश्न' : 'Your Question',
              hintText: lang == 'hi' ? 'अपना प्रश्न यहाँ लिखें...' : 'Type your question here...',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _sending ? null : _submit,
              icon: _sending
                  ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Icon(Icons.send),
              label: Text(lang == 'hi' ? 'भेजें' : 'Send to NAGA'),
            ),
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _SmallOutlinedButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  const _SmallOutlinedButton({required this.label, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onPressed,
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
      child: Text(label, style: const TextStyle(fontSize: 12)),
    );
  }
}
