import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/student_model.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class StudyScreen extends StatefulWidget {
  const StudyScreen({super.key});

  @override
  State<StudyScreen> createState() => _StudyScreenState();
}

class _StudyScreenState extends State<StudyScreen> {
  final _searchCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final List<_NoteEntry> _notes = [];
  bool _searching = false;

  static const _loadingPhrases = [
    'Looking up the concept…',
    'Generating study notes…',
    'Preparing solved examples…',
    'Checking exam tips…',
  ];

  @override
  void dispose() {
    _searchCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _fetchNotes(String topic) async {
    if (topic.trim().isEmpty) return;
    final id = DateTime.now().millisecondsSinceEpoch.toString();
    setState(() {
      _notes.add(_NoteEntry(id: id, topic: topic, loading: true));
      _searching = false;
    });
    _searchCtrl.clear();
    // scroll to top of new card after frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
    try {
      final result = await ApiService().getStudyNotes(topic.trim());
      final notes = result['notes'] as String? ?? '';
      final videos = (result['youtube_videos'] as List<dynamic>? ?? [])
          .map((v) => _Video(
                title: v['title'] as String? ?? '',
                url: v['url'] as String? ?? '',
              ))
          .toList();
      setState(() {
        final idx = _notes.indexWhere((n) => n.id == id);
        if (idx >= 0) {
          _notes[idx] = _NoteEntry(id: id, topic: topic, notes: notes, videos: videos);
        }
      });
    } catch (e) {
      setState(() {
        final idx = _notes.indexWhere((n) => n.id == id);
        if (idx >= 0) {
          _notes[idx] = _NoteEntry(id: id, topic: topic, error: 'Could not load notes. Please try again.');
        }
      });
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final student = auth.student;
    final lang = student?.preferredLanguage ?? 'en';
    final weakness = student?.weaknessMap ?? [];
    final sorted = [...weakness]..sort((a, b) => a.scorePct.compareTo(b.scorePct));

    return Column(
      children: [
        // ── Search Bar ──
        Material(
          color: Colors.white,
          elevation: 1,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _searchCtrl,
                    decoration: InputDecoration(
                      hintText: lang == 'hi' ? 'कोई भी विषय खोजें…' : 'Enter any topic to get notes…',
                      prefixIcon: const Icon(Icons.search, size: 20),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    ),
                    onSubmitted: _fetchNotes,
                    textInputAction: TextInputAction.search,
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  icon: const Icon(Icons.arrow_forward),
                  onPressed: () => _fetchNotes(_searchCtrl.text),
                  style: IconButton.styleFrom(backgroundColor: AppTheme.primary),
                ),
              ],
            ),
          ),
        ),

        // ── Content area ──
        Expanded(
          child: _notes.isEmpty
              ? _EmptyState(weakTopics: sorted.take(4).cast<WeaknessMap>().toList(), onTap: _fetchNotes, lang: lang)
              : ListView.separated(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.all(16),
                  itemCount: _notes.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 16),
                  itemBuilder: (_, i) => _NoteCard(
                    entry: _notes[i],
                    loadingPhrases: _loadingPhrases,
                  ),
                ),
        ),

        // ── Focus Areas strip (show weak topics for quick access) ──
        if (sorted.isNotEmpty && _notes.isEmpty)
          const SizedBox.shrink(),
      ],
    );
  }
}

// ── Empty state ────────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  final List<WeaknessMap> weakTopics;
  final ValueChanged<String> onTap;
  final String lang;
  const _EmptyState({required this.weakTopics, required this.onTap, required this.lang});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const SizedBox(height: 24),
        const Center(child: Icon(Icons.menu_book_outlined, size: 64, color: AppTheme.primary)),
        const SizedBox(height: 16),
        Center(child: Text(
          lang == 'hi' ? 'अध्ययन सामग्री' : 'Study Materials',
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: AppTheme.primary),
        )),
        const SizedBox(height: 6),
        Center(child: Text(
          lang == 'hi'
              ? 'किसी भी विषय पर Concept + Solved Examples पाएं'
              : 'Get Concept Overview + Solved Examples for any topic',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey.shade600),
        )),
        if (weakTopics.isNotEmpty) ...[
          const SizedBox(height: 28),
          Text(
            lang == 'hi' ? 'आपके कमजोर विषय:' : 'Your weak areas — tap to study:',
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
          ),
          const SizedBox(height: 10),
          ...weakTopics.map((w) {
            final pct = w.scorePct * 100;
            final color = pct >= 60 ? Colors.green : pct >= 40 ? Colors.orange : Colors.red;
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                leading: CircleAvatar(
                  radius: 20,
                  backgroundColor: color.withOpacity(0.15),
                  child: Text(
                    '${pct.round()}%',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: color),
                  ),
                ),
                title: Text(w.topic, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(w.subject, style: const TextStyle(fontSize: 12)),
                trailing: const Icon(Icons.arrow_forward_ios, size: 14),
                onTap: () => onTap(w.topic),
              ),
            );
          }),
        ] else ...[
          const SizedBox(height: 28),
          const Text('Try asking about:', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 10),
          ...['LCM and HCF', 'Simple Interest', "Newton's Laws", 'Photosynthesis'].map((s) => Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: const Icon(Icons.lightbulb_outline, color: AppTheme.secondary),
              title: Text(s),
              trailing: const Icon(Icons.arrow_forward_ios, size: 14),
              onTap: () => onTap(s),
            ),
          )),
        ],
      ],
    );
  }
}

// ── Note card ──────────────────────────────────────────────────────────────────

class _NoteCard extends StatefulWidget {
  final _NoteEntry entry;
  final List<String> loadingPhrases;
  const _NoteCard({required this.entry, required this.loadingPhrases});

  @override
  State<_NoteCard> createState() => _NoteCardState();
}

class _NoteCardState extends State<_NoteCard> {
  int _phraseIdx = 0;

  @override
  void initState() {
    super.initState();
    if (widget.entry.loading) _cyclePhrase();
  }

  void _cyclePhrase() {
    Future.delayed(const Duration(milliseconds: 1600), () {
      if (!mounted || !widget.entry.loading) return;
      setState(() => _phraseIdx = (_phraseIdx + 1) % widget.loadingPhrases.length);
      _cyclePhrase();
    });
  }

  @override
  Widget build(BuildContext context) {
    final e = widget.entry;
    if (e.loading) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                const SizedBox(
                  width: 16, height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                ),
                const SizedBox(width: 10),
                Text(
                  widget.loadingPhrases[_phraseIdx],
                  style: const TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w500),
                ),
              ]),
              const SizedBox(height: 14),
              Container(height: 10, width: double.infinity, color: Colors.grey.shade200),
              const SizedBox(height: 6),
              Container(height: 10, width: 200, color: Colors.grey.shade200),
              const SizedBox(height: 6),
              Container(height: 10, width: 260, color: Colors.grey.shade200),
            ],
          ),
        ),
      );
    }

    if (e.error != null) {
      return Card(
        color: Colors.red.shade50,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(e.error!, style: const TextStyle(color: Colors.red)),
        ),
      );
    }

    return Card(
      clipBehavior: Clip.hardEdge,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Container(
            color: AppTheme.primary.withOpacity(0.06),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                const Icon(Icons.menu_book_outlined, size: 18, color: AppTheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    e.topic,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AppTheme.primary,
                      fontSize: 15,
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Notes (markdown)
          if (e.notes != null && e.notes!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.all(16),
              child: MarkdownBody(
                data: e.notes!,
                shrinkWrap: true,
                onTapLink: (_, href, __) async {
                  if (href != null) {
                    final uri = Uri.tryParse(href);
                    if (uri != null) await launchUrl(uri, mode: LaunchMode.externalApplication);
                  }
                },
              ),
            ),
          // Videos
          if (e.videos != null && e.videos!.isNotEmpty) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: const Text(
                '📺  Related Videos',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
              ),
            ),
            ...e.videos!.map((v) => ListTile(
              dense: true,
              leading: const Icon(Icons.play_circle_outline, color: Colors.red, size: 20),
              title: Text(v.title, style: const TextStyle(fontSize: 13)),
              onTap: () async {
                final uri = Uri.tryParse(v.url);
                if (uri != null) await launchUrl(uri, mode: LaunchMode.externalApplication);
              },
            )),
            const SizedBox(height: 8),
          ],
        ],
      ),
    );
  }
}

// ── Data classes ───────────────────────────────────────────────────────────────

class _NoteEntry {
  final String id;
  final String topic;
  final bool loading;
  final String? notes;
  final List<_Video>? videos;
  final String? error;

  const _NoteEntry({
    required this.id,
    required this.topic,
    this.loading = false,
    this.notes,
    this.videos,
    this.error,
  });
}

class _Video {
  final String title;
  final String url;
  const _Video({required this.title, required this.url});
}
