import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Search, X, MessageSquare } from 'lucide-react';
import { getFAQs, createFAQ, updateFAQ, deleteFAQ, FAQ } from '@/lib/api';

const categories = ['general', 'services', 'pricing', 'booking', 'policies', 'aftercare', 'products'];

export function FAQs() {
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingFaq, setEditingFaq] = useState<FAQ | null>(null);
  const [formData, setFormData] = useState({
    question_pattern: '',
    answer: '',
    category: 'general',
  });
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    loadFAQs();
  }, []);

  const loadFAQs = async () => {
    try {
      const data = await getFAQs();
      setFaqs(data);
    } catch (error) {
      console.error('Error loading FAQs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (editingFaq) {
        await updateFAQ(editingFaq.id, formData);
      } else {
        await createFAQ(formData);
      }
      setShowModal(false);
      setEditingFaq(null);
      setFormData({ question_pattern: '', answer: '', category: 'general' });
      loadFAQs();
    } catch (error) {
      console.error('Error saving FAQ:', error);
    }
  };

  const handleEdit = (faq: FAQ) => {
    setEditingFaq(faq);
    setFormData({
      question_pattern: faq.question_pattern,
      answer: faq.answer,
      category: faq.category,
    });
    setShowModal(true);
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this FAQ?')) {
      try {
        await deleteFAQ(id);
        loadFAQs();
      } catch (error) {
        console.error('Error deleting FAQ:', error);
      }
    }
  };

  const filteredFaqs = filter === 'all'
    ? faqs
    : faqs.filter((faq) => faq.category === filter);

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      general: 'bg-gray-100 text-gray-700',
      services: 'bg-pink-100 text-pink-700',
      pricing: 'bg-green-100 text-green-700',
      booking: 'bg-blue-100 text-blue-700',
      policies: 'bg-purple-100 text-purple-700',
      aftercare: 'bg-yellow-100 text-yellow-700',
      products: 'bg-teal-100 text-teal-700',
    };
    return colors[category] || colors.general;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">FAQ Knowledge Base</h1>
          <p className="text-gray-500 mt-1">Manage what Luna can answer about your studio</p>
        </div>
        <button
          onClick={() => {
            setEditingFaq(null);
            setFormData({ question_pattern: '', answer: '', category: 'general' });
            setShowModal(true);
          }}
          className="flex items-center gap-2 px-4 py-2.5 bg-pink-500 text-white rounded-lg hover:bg-pink-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add FAQ
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            filter === 'all'
              ? 'bg-pink-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All ({faqs.length})
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium capitalize transition-colors ${
              filter === cat
                ? 'bg-pink-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {cat} ({faqs.filter((f) => f.category === cat).length})
          </button>
        ))}
      </div>

      {/* FAQ List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
          </div>
        ) : filteredFaqs.length === 0 ? (
          <div className="p-12 text-center">
            <MessageSquare className="w-12 h-12 text-gray-300 mx-auto" />
            <p className="mt-4 text-gray-500">No FAQs found</p>
            <button
              onClick={() => setShowModal(true)}
              className="mt-4 text-pink-500 hover:text-pink-600"
            >
              Add your first FAQ
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredFaqs.map((faq) => (
              <div key={faq.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${getCategoryColor(faq.category)}`}>
                        {faq.category}
                      </span>
                      {!faq.active && (
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="font-semibold text-gray-900 mb-2">{faq.question_pattern}</p>
                    <p className="text-gray-600">{faq.answer}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleEdit(faq)}
                      className="p-2 text-gray-400 hover:text-pink-500 hover:bg-pink-50 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(faq.id)}
                      className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-hidden shadow-xl">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                {editingFaq ? 'Edit FAQ' : 'Add New FAQ'}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category
                </label>
                <select
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat} className="capitalize">
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Question Pattern
                </label>
                <input
                  type="text"
                  value={formData.question_pattern}
                  onChange={(e) => setFormData({ ...formData, question_pattern: e.target.value })}
                  placeholder="e.g., how much are your lashes"
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
                  required
                />
                <p className="mt-1 text-xs text-gray-500">
                  Keywords that trigger this answer (case-insensitive)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Answer
                </label>
                <textarea
                  value={formData.answer}
                  onChange={(e) => setFormData({ ...formData, answer: e.target.value })}
                  placeholder="The response Luna should give"
                  rows={4}
                  className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent resize-none"
                  required
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2.5 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2.5 bg-pink-500 text-white rounded-lg hover:bg-pink-600 transition-colors"
                >
                  {editingFaq ? 'Save Changes' : 'Add FAQ'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
