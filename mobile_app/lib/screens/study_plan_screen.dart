import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'diagnostic_screen.dart';

class StudyPlanScreen extends StatefulWidget {
  const StudyPlanScreen({super.key});

  @override
  State<StudyPlanScreen> createState() => _StudyPlanScreenState();
}

class _StudyPlanScreenState extends State<StudyPlanScreen> {
  bool _loading = true;
  bool _generating = false;
  String? _error;
  Map<String, dynamic>? _activePlan;
  Map<String, dynamic>? _proposedPlan;

  static const _generatePhrases = [
    'Analysing your weak areas…',
    'Building your weekly schedule…',
    'Calibrating difficulty for each topic…',
    'Finalising your year plan…',
  ];
  int _phraseIdx = 0;
  Timer? _phraseTimer;

  @override
  void initState() {
    super.initState();
    _loadPlans();
  }

  @override
  void dispose() {
    _phraseTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadPlans() async {
    setState(() { _loading = true; _error = null; });
    try {
      // Refresh student profile first so diagnostic_done is current
      // (cached profile may be stale if diagnostic was completed after last login)
      await context.read<AuthProvider>().refreshStudent();
      final results = await Future.wait([
        ApiService().getDabbuStudyPlan(),
        ApiService().getProposedStudyPlan(),
      ]);
      setState(() {
        _activePlan = results[0]['plan'] as Map<String, dynamic>?;
        _proposedPlan = results[1]['plan'] as Map<String, dynamic>?;
        _loading = false;
      });
    } catch (e) {
      setState(() { _error = 'Could not load study plan.'; _loading = false; });
    }
  }

  Future<void> _generate() async {
    setState(() { _generating = true; _phraseIdx = 0; });
    _phraseTimer = Timer.periodic(const Duration(milliseconds: 1800), (_) {
      if (mounted) setState(() => _phraseIdx = (_phraseIdx + 1) % _generatePhrases.length);
    });
    try {
      final res = await ApiService().generateStudyPlan();
      _phraseTimer?.cancel();
      setState(() {
        _proposedPlan = res['plan'] as Map<String, dynamic>?;
        _generating = false;
      });
    } catch (e) {
      _phraseTimer?.cancel();
      setState(() {
        _error = 'Could not generate study plan. Please try again.';
        _generating = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final student = context.watch<AuthProvider>().student;
    final diagnosticDone = student?.diagnosticDone ?? false;

    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator(color: AppTheme.primary)));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Study Plan'),
        actions: [
          if (_activePlan != null || _proposedPlan != null)
            IconButton(icon: const Icon(Icons.refresh), onPressed: _loadPlans),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadPlans,
        child: _buildBody(diagnosticDone),
      ),
    );
  }

  Widget _buildBody(bool diagnosticDone) {
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 12),
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _loadPlans, child: const Text('Retry')),
          ]),
        ),
      );
    }

    if (!diagnosticDone) return _DiagnosticGate();

    if (_generating) return _GeneratingView(phrase: _generatePhrases[_phraseIdx]);

    if (_activePlan != null) return _ActivePlanView(plan: _activePlan!, onRefresh: _loadPlans);

    if (_proposedPlan != null) return _ProposedView(plan: _proposedPlan!, onRefresh: _loadPlans);

    return _GeneratePrompt(onGenerate: _generate);
  }
}

// ── Diagnostic gate ────────────────────────────────────────────────────────────

class _DiagnosticGate extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.assignment_outlined, size: 64, color: AppTheme.secondary),
          const SizedBox(height: 20),
          const Text('Complete the diagnostic first',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text('Dabbu needs your diagnostic results to build a personalised plan.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey.shade600)),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            icon: const Icon(Icons.quiz_outlined),
            label: const Text('Go to Diagnostic'),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const DiagnosticScreen())),
          ),
        ]),
      ),
    );
  }
}

// ── Generating spinner ─────────────────────────────────────────────────────────

class _GeneratingView extends StatelessWidget {
  final String phrase;
  const _GeneratingView({required this.phrase});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const SizedBox(
            width: 48, height: 48,
            child: CircularProgressIndicator(strokeWidth: 3, color: AppTheme.primary),
          ),
          const SizedBox(height: 24),
          Text(phrase,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppTheme.primary)),
          const SizedBox(height: 8),
          Text('NAGA will review before it goes live.',
              style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
        ]),
      ),
    );
  }
}

// ── Generate prompt ────────────────────────────────────────────────────────────

class _GeneratePrompt extends StatelessWidget {
  final VoidCallback onGenerate;
  const _GeneratePrompt({required this.onGenerate});

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(24), children: [
      const SizedBox(height: 24),
      Center(
        child: Container(
          width: 80, height: 80,
          decoration: BoxDecoration(
            color: AppTheme.primary.withOpacity(0.1),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Icon(Icons.calendar_month_outlined, size: 40, color: AppTheme.primary),
        ),
      ),
      const SizedBox(height: 20),
      const Center(
        child: Text('Build your study plan',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
      ),
      const SizedBox(height: 8),
      Center(
        child: Text(
          'Dabbu creates a day-by-day schedule tailored to your weak areas.\nNAGA reviews it before it goes live.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey.shade600),
        ),
      ),
      const SizedBox(height: 32),
      // Feature chips
      ...[
        ('📅', 'Full year schedule', 'Week-by-week breakdown for every topic'),
        ('🎯', 'Weak area focus', 'Double weight on your lowest-scoring topics'),
        ('📊', 'Progress tracking', 'Mark blocks done, track completion rate'),
        ('👨‍🏫', 'NAGA reviewed', 'Your mentor checks the plan before you see it'),
      ].map((f) => Card(
        margin: const EdgeInsets.only(bottom: 10),
        child: ListTile(
          leading: Text(f.$1, style: const TextStyle(fontSize: 24)),
          title: Text(f.$2, style: const TextStyle(fontWeight: FontWeight.w600)),
          subtitle: Text(f.$3, style: const TextStyle(fontSize: 12)),
        ),
      )),
      const SizedBox(height: 24),
      ElevatedButton.icon(
        icon: const Icon(Icons.auto_awesome),
        label: const Text('Generate My Study Plan'),
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        onPressed: onGenerate,
      ),
    ]);
  }
}

// ── Proposed (awaiting NAGA) ───────────────────────────────────────────────────

class _ProposedView extends StatelessWidget {
  final Map<String, dynamic> plan;
  final VoidCallback onRefresh;
  const _ProposedView({required this.plan, required this.onRefresh});

  @override
  Widget build(BuildContext context) {
    final weeks = (plan['weeks'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    return ListView(padding: const EdgeInsets.all(16), children: [
      // Status banner
      Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.amber.shade50,
          border: Border.all(color: Colors.amber.shade200),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(children: [
          const SizedBox(
            width: 18, height: 18,
            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.amber),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Awaiting NAGA\'s review',
                style: TextStyle(fontWeight: FontWeight.w700, color: Colors.amber)),
            Text('Your plan is ready — NAGA will approve it shortly.',
                style: TextStyle(fontSize: 12, color: Colors.amber.shade700)),
          ])),
        ]),
      ),
      const SizedBox(height: 16),
      _PlanSummaryCard(plan: plan),
      const SizedBox(height: 16),
      Text('${weeks.length} weeks planned',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
      const SizedBox(height: 8),
      ...weeks.take(4).map((w) => _WeekTile(week: w, readOnly: true)),
      if (weeks.length > 4)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text('+ ${weeks.length - 4} more weeks',
              style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
        ),
    ]);
  }
}

// ── Active plan ────────────────────────────────────────────────────────────────

class _ActivePlanView extends StatefulWidget {
  final Map<String, dynamic> plan;
  final VoidCallback onRefresh;
  const _ActivePlanView({required this.plan, required this.onRefresh});

  @override
  State<_ActivePlanView> createState() => _ActivePlanViewState();
}

class _ActivePlanViewState extends State<_ActivePlanView> {
  int _selectedWeek = 1;
  String? _selectedDay;

  @override
  void initState() {
    super.initState();
    _initSelection();
  }

  void _initSelection() {
    final weeks = (widget.plan['weeks'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    final today = DateTime.now().toIso8601String().substring(0, 10);
    // Find the current week
    Map<String, dynamic>? curWeek;
    for (final w in weeks) {
      final start = w['start_date'] as String? ?? '';
      final end = w['end_date'] as String? ?? '';
      if (start.isNotEmpty && end.isNotEmpty && today.compareTo(start) >= 0 && today.compareTo(end) <= 0) {
        curWeek = w;
        break;
      }
    }
    final targetWeek = curWeek ?? (weeks.isNotEmpty ? weeks.first : null);
    if (targetWeek == null) return;
    _selectedWeek = targetWeek['week_number'] as int? ?? 1;
    // Default to today if it's a study day, else first non-rest day
    final days = (targetWeek['days'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    final todayEntry = days.where((d) => d['day_date'] == today && !(d['is_rest_day'] as bool? ?? false)).firstOrNull;
    final firstStudy = days.where((d) => !(d['is_rest_day'] as bool? ?? false)).firstOrNull;
    _selectedDay = todayEntry?['day_date'] as String? ?? firstStudy?['day_date'] as String?;
  }

  Map<String, dynamic>? _getSelectedDayData(List<Map<String, dynamic>> weeks) {
    for (final w in weeks) {
      if (w['week_number'] == _selectedWeek) {
        final days = (w['days'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
        if (_selectedDay != null) {
          return days.where((d) => d['day_date'] == _selectedDay).firstOrNull;
        }
        return days.where((d) => !(d['is_rest_day'] as bool? ?? false)).firstOrNull;
      }
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final weeks = (widget.plan['weeks'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    final selectedWeekData = weeks.firstWhere(
      (w) => w['week_number'] == _selectedWeek,
      orElse: () => weeks.isNotEmpty ? weeks.first : {},
    );
    final days = (selectedWeekData['days'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
    final selectedDayData = _getSelectedDayData(weeks);

    return Column(children: [
      // Plan summary
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
        child: _PlanSummaryCard(plan: widget.plan),
      ),
      const SizedBox(height: 10),
      // Week selector
      SizedBox(
        height: 40,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          itemCount: weeks.length,
          itemBuilder: (_, i) {
            final w = weeks[i];
            final num = w['week_number'] as int;
            final active = num == _selectedWeek;
            return GestureDetector(
              onTap: () {
                final wDays = (w['days'] as List<dynamic>? ?? []).cast<Map<String, dynamic>>();
                final today = DateTime.now().toIso8601String().substring(0, 10);
                final todayEntry = wDays.where((d) => d['day_date'] == today && !(d['is_rest_day'] as bool? ?? false)).firstOrNull;
                final firstStudy = wDays.where((d) => !(d['is_rest_day'] as bool? ?? false)).firstOrNull;
                setState(() {
                  _selectedWeek = num;
                  _selectedDay = todayEntry?['day_date'] as String? ?? firstStudy?['day_date'] as String?;
                });
              },
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 4),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: active ? AppTheme.primary : Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text('Wk $num',
                  style: TextStyle(
                    color: active ? Colors.white : Colors.grey.shade700,
                    fontWeight: active ? FontWeight.w700 : FontWeight.normal,
                    fontSize: 13,
                  ),
                ),
              ),
            );
          },
        ),
      ),
      const SizedBox(height: 8),
      // Day selector strip
      SizedBox(
        height: 60,
        child: ListView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          children: days.map((day) {
            final date = day['day_date'] as String? ?? '';
            final isRest = day['is_rest_day'] as bool? ?? false;
            final dow = (day['day_of_week'] as String? ?? '').substring(0, 3);
            final dayNum = date.length >= 10 ? int.tryParse(date.substring(8, 10)) ?? 0 : 0;
            final isSelected = date == _selectedDay;
            final today = DateTime.now().toIso8601String().substring(0, 10);
            final isToday = date == today;
            return GestureDetector(
              onTap: () => setState(() => _selectedDay = date),
              child: Container(
                width: 44,
                margin: const EdgeInsets.symmetric(horizontal: 3),
                decoration: BoxDecoration(
                  color: isSelected ? AppTheme.primary : isToday ? AppTheme.primary.withOpacity(0.1) : Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: isToday && !isSelected ? Border.all(color: AppTheme.primary, width: 1.5) : null,
                ),
                child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Text(dow,
                    style: TextStyle(fontSize: 10, color: isSelected ? Colors.white70 : Colors.grey.shade500, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text('$dayNum',
                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800,
                      color: isSelected ? Colors.white : isRest ? Colors.grey.shade400 : Colors.grey.shade800)),
                  if (isRest)
                    Text('—', style: TextStyle(fontSize: 9, color: Colors.grey.shade400))
                  else
                    Text('${(day['blocks'] as List?)?.length ?? 0}✓',
                      style: TextStyle(fontSize: 9, color: isSelected ? Colors.white70 : Colors.grey.shade500)),
                ]),
              ),
            );
          }).toList(),
        ),
      ),
      const SizedBox(height: 8),
      // Day schedule
      Expanded(
        child: selectedDayData == null
            ? const Center(child: Text('Select a day above'))
            : _DayScheduleView(day: selectedDayData),
      ),
    ]);
  }
}

// ── Day schedule view (hour-by-hour) ──────────────────────────────────────────

class _DayScheduleView extends StatelessWidget {
  final Map<String, dynamic> day;
  const _DayScheduleView({required this.day});

  static const _typeColors = <String, Color>{
    'study':    Color(0xFF2563EB),  // blue-600
    'practice': Color(0xFFC026D3),  // fuchsia-600
    'mock':     Color(0xFFDC2626),  // red-600
    'revision': Color(0xFFF59E0B),  // amber-500
    'rest':     Color(0xFF9CA3AF),
  };
  static const _typeBg = <String, Color>{
    'study':    Color(0xFFEFF6FF),
    'practice': Color(0xFFFDF4FF),
    'mock':     Color(0xFFFEF2F2),
    'revision': Color(0xFFFFFBEB),
  };
  static const _typeLabels = <String, String>{
    'study': 'STUDY', 'practice': 'PRACTICE', 'mock': 'MOCK', 'revision': 'REVISION',
  };
  static const _typeIcons = <String, IconData>{
    'study': Icons.menu_book_outlined, 'practice': Icons.quiz_outlined,
    'mock': Icons.timer_outlined, 'revision': Icons.replay_outlined,
  };

  String _fmt12h(int hour) {
    final h = hour % 12 == 0 ? 12 : hour % 12;
    final ampm = hour < 12 ? 'AM' : 'PM';
    return '$h:00 $ampm';
  }

  @override
  Widget build(BuildContext context) {
    final isRest = day['is_rest_day'] as bool? ?? false;
    final dayName = day['day_of_week'] as String? ?? '';
    final date = day['day_date'] as String? ?? '';
    final totalHours = (day['total_hours'] as num?)?.toStringAsFixed(0) ?? '0';

    if (isRest) {
      return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.self_improvement, size: 48, color: Colors.grey),
        const SizedBox(height: 12),
        Text('$dayName — Rest Day', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
        const SizedBox(height: 4),
        const Text("Take a break — you've earned it.", style: TextStyle(color: Colors.grey)),
      ]));
    }

    final blocks = (day['blocks'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>()
        ..sort((a, b) => (a['start_hour'] as int? ?? 0).compareTo(b['start_hour'] as int? ?? 0));

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      children: [
        // Day header
        Row(children: [
          Expanded(child: Text('$dayName${date.length >= 10 ? " · ${date.substring(5)}" : ""}',
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15))),
          Text('${blocks.length} sessions · ${totalHours}h',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
        ]),
        const SizedBox(height: 12),
        // Timeline entries
        ...blocks.asMap().entries.map((entry) {
          final b = entry.value;
          final isLast = entry.key == blocks.length - 1;
          final type = b['session_type'] as String? ?? 'study';
          final startHour = b['start_hour'] as int? ?? 7;
          final durHours = b['duration_hours'] as int? ?? 2;
          final endHour = startHour + durHours;
          final subject = b['subject'] as String? ?? '';
          final topic = b['topic'] as String? ?? '';
          final color = _typeColors[type] ?? const Color(0xFF2563EB);
          final bg = _typeBg[type] ?? const Color(0xFFEFF6FF);
          final icon = _typeIcons[type] ?? Icons.school_outlined;
          final label = _typeLabels[type] ?? type.toUpperCase();

          return IntrinsicHeight(
            child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              // Time column
              SizedBox(width: 76, child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Padding(
                  padding: const EdgeInsets.only(right: 12, top: 10),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Text(_fmt12h(startHour),
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF374151))),
                    Text('– ${_fmt12h(endHour)}',
                        style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
                    Text('${durHours}h', style: TextStyle(fontSize: 10, color: Colors.grey.shade400)),
                  ]),
                ),
              ])),
              // Connector
              Column(children: [
                Container(width: 10, height: 10, margin: const EdgeInsets.only(top: 12),
                    decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
                if (!isLast)
                  Expanded(child: Container(width: 2, color: Colors.grey.shade200)),
              ]),
              const SizedBox(width: 10),
              // Session card
              Expanded(child: Container(
                margin: EdgeInsets.only(bottom: isLast ? 0 : 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: bg,
                  borderRadius: BorderRadius.circular(12),
                  border: Border(left: BorderSide(color: color, width: 3)),
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Icon(icon, size: 13, color: color),
                    const SizedBox(width: 4),
                    Text(label, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                        color: color, letterSpacing: 0.8)),
                  ]),
                  if (topic.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(topic, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                  ],
                  if (subject.isNotEmpty)
                    Text(subject, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                ]),
              )),
            ]),
          );
        }),
        const SizedBox(height: 16),
      ],
    );
  }
}

// ── Shared widgets ─────────────────────────────────────────────────────────────

class _PlanSummaryCard extends StatelessWidget {
  final Map<String, dynamic> plan;
  const _PlanSummaryCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    final exam = (plan['exam_target'] as String? ?? '').toUpperCase().replaceAll('_', ' ');
    final months = plan['duration_months'] as int? ?? 6;
    final weeks = (plan['weeks'] as List<dynamic>? ?? []).length;
    final hours = plan['total_study_hours'] as num? ?? 0;
    final startDate = plan['start_date'] as String? ?? '';
    final endDate = plan['end_date'] as String? ?? '';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.primary, Color(0xFF7C3AED)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(exam, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 18)),
        const SizedBox(height: 4),
        Text('$months months · $weeks weeks · ${hours.toStringAsFixed(0)}h total',
            style: const TextStyle(color: Colors.white70, fontSize: 13)),
        if (startDate.isNotEmpty && endDate.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text('${startDate.substring(0, 10)} → ${endDate.substring(0, 10)}',
              style: const TextStyle(color: Colors.white60, fontSize: 12)),
        ],
      ]),
    );
  }
}

class _WeekTile extends StatelessWidget {
  final Map<String, dynamic> week;
  final bool readOnly;
  const _WeekTile({required this.week, this.readOnly = false});

  @override
  Widget build(BuildContext context) {
    final weekNum = week['week_number'] as int? ?? 0;
    final theme = week['theme'] as String? ?? '';
    final days = (week['days'] as List<dynamic>? ?? []).length;
    final hours = (week['total_hours'] as num?) ?? 0;
    return Card(
      margin: const EdgeInsets.only(bottom: 6),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppTheme.primary.withOpacity(0.1),
          child: Text('$weekNum', style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w700)),
        ),
        title: Text(theme.isNotEmpty ? theme : 'Week $weekNum',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: Text('$days days · ${hours.toStringAsFixed(1)}h',
            style: const TextStyle(fontSize: 12)),
        trailing: const Icon(Icons.chevron_right, size: 18),
      ),
    );
  }
}
