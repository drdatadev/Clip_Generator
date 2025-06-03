"""
Topic Classifier Module

This module handles automatic classification of video clips into economic topic categories.
Uses both keyword matching and AI analysis for accurate categorization.
"""

import re
from typing import Dict, List, Optional
from ..config import config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TopicClassifier:
    """
    Classifies video clips into economic topic categories.
    
    Uses a combination of keyword matching, context analysis, and content patterns
    to automatically categorize clips for organized storage and retrieval.
    """
    
    def __init__(self):
        """Initialize the topic classifier with category definitions."""
        self.categories = config.TOPIC_CATEGORIES
        self.category_weights = self._calculate_category_weights()
        
    def _calculate_category_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate weights for keywords based on specificity and importance.
        
        Returns:
            Dictionary of categories with keyword weights
        """
        weights = {}
        
        for category, keywords in self.categories.items():
            if category == 'general':
                continue
                
            category_weights = {}
            for keyword in keywords:
                # Weight longer, more specific terms higher
                word_count = len(keyword.split())
                base_weight = 1.0
                
                # Multi-word phrases get higher weight
                if word_count > 1:
                    base_weight *= 1.5
                
                # Specific economic terms get bonus weight
                specific_terms = ['federal reserve', 'interest rate', 'cpi', 'gdp', 'unemployment rate']
                if keyword in specific_terms:
                    base_weight *= 2.0
                
                category_weights[keyword] = base_weight
            
            weights[category] = category_weights
        
        return weights
    
    def classify_by_description(self, description: str) -> Dict:
        """
        Classify clip based on user description.
        
        Args:
            description: User's clip description
            
        Returns:
            Dictionary with classification results
        """
        description_lower = description.lower()
        category_scores = {}
        
        # Calculate scores for each category
        for category, keywords in self.categories.items():
            if category == 'general':
                continue
                
            score = 0.0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in description_lower:
                    weight = self.category_weights[category].get(keyword, 1.0)
                    score += weight
                    matched_keywords.append(keyword)
            
            if score > 0:
                category_scores[category] = {
                    'score': score,
                    'matched_keywords': matched_keywords
                }
        
        # Determine best category
        if category_scores:
            best_category = max(category_scores, key=lambda x: category_scores[x]['score'])
            confidence = min(category_scores[best_category]['score'] / 5.0, 1.0)  # Normalize to 0-1
            
            return {
                'primary_category': best_category,
                'confidence_score': confidence,
                'all_scores': category_scores,
                'method': 'description_keywords'
            }
        else:
            return {
                'primary_category': 'general',
                'confidence_score': 0.0,
                'all_scores': {},
                'method': 'default_fallback'
            }
    
    def classify_by_content(self, transcript_segment: str) -> Dict:
        """
        Classify clip based on actual transcript content.
        
        Args:
            transcript_segment: Relevant portion of transcript
            
        Returns:
            Dictionary with classification results
        """
        if not transcript_segment or not transcript_segment.strip():
            return {
                'primary_category': 'general',
                'confidence_score': 0.0,
                'all_scores': {},
                'method': 'empty_content'
            }
        
        content_lower = transcript_segment.lower()
        category_scores = {}
        
        # Calculate scores for each category
        for category, keywords in self.categories.items():
            if category == 'general':
                continue
                
            score = 0.0
            matched_keywords = []
            keyword_positions = []
            
            for keyword in keywords:
                # Count all occurrences of keyword
                occurrences = len(re.findall(r'\b' + re.escape(keyword) + r'\b', content_lower))
                if occurrences > 0:
                    weight = self.category_weights[category].get(keyword, 1.0)
                    score += weight * occurrences
                    matched_keywords.append(keyword)
                    
                    # Track positions for context analysis
                    for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', content_lower):
                        keyword_positions.append(match.start())
            
            if score > 0:
                # Bonus for keyword density and clustering
                content_length = len(content_lower)
                density_bonus = (score / content_length) * 1000  # Keywords per 1000 chars
                
                # Clustering bonus (keywords appearing close together)
                clustering_bonus = self._calculate_clustering_bonus(keyword_positions, content_length)
                
                final_score = score + density_bonus + clustering_bonus
                
                category_scores[category] = {
                    'score': final_score,
                    'base_score': score,
                    'density_bonus': density_bonus,
                    'clustering_bonus': clustering_bonus,
                    'matched_keywords': matched_keywords,
                    'keyword_count': len(matched_keywords)
                }
        
        # Determine best category
        if category_scores:
            best_category = max(category_scores, key=lambda x: category_scores[x]['score'])
            max_score = category_scores[best_category]['score']
            
            # Calculate confidence based on score and keyword diversity
            keyword_diversity = len(category_scores[best_category]['matched_keywords'])
            confidence = min((max_score / 10.0) * (1 + keyword_diversity * 0.1), 1.0)
            
            return {
                'primary_category': best_category,
                'confidence_score': confidence,
                'all_scores': category_scores,
                'method': 'content_analysis'
            }
        else:
            return {
                'primary_category': 'general',
                'confidence_score': 0.0,
                'all_scores': {},
                'method': 'no_keywords_found'
            }
    
    def _calculate_clustering_bonus(self, positions: List[int], content_length: int) -> float:
        """
        Calculate bonus score for keywords appearing close together.
        
        Args:
            positions: List of keyword positions in text
            content_length: Total length of content
            
        Returns:
            Clustering bonus score
        """
        if len(positions) < 2:
            return 0.0
        
        positions.sort()
        clustering_bonus = 0.0
        
        for i in range(1, len(positions)):
            distance = positions[i] - positions[i-1]
            # Bonus for keywords within 100 characters of each other
            if distance <= 100:
                clustering_bonus += (100 - distance) / 100.0
        
        return clustering_bonus
    
    def classify_combined(self, description: str, transcript_segment: str, 
                         start_time: float, end_time: float) -> Dict:
        """
        Classify using both description and content analysis.
        
        Args:
            description: User's clip description
            transcript_segment: Relevant transcript content
            start_time: Clip start time
            end_time: Clip end time
            
        Returns:
            Combined classification results
        """
        # Get classifications from both methods
        desc_result = self.classify_by_description(description)
        content_result = self.classify_by_content(transcript_segment)
        
        # If both methods agree, high confidence
        if desc_result['primary_category'] == content_result['primary_category']:
            combined_confidence = min((desc_result['confidence_score'] + content_result['confidence_score']) / 1.5, 1.0)
            
            return {
                'primary_category': desc_result['primary_category'],
                'confidence_score': combined_confidence,
                'description_result': desc_result,
                'content_result': content_result,
                'method': 'combined_agreement',
                'clip_duration': end_time - start_time
            }
        
        # If methods disagree, use the one with higher confidence
        if desc_result['confidence_score'] > content_result['confidence_score']:
            primary_result = desc_result
            secondary_result = content_result
            method = 'description_primary'
        else:
            primary_result = content_result
            secondary_result = desc_result
            method = 'content_primary'
        
        # Reduce confidence when methods disagree
        adjusted_confidence = primary_result['confidence_score'] * 0.7
        
        return {
            'primary_category': primary_result['primary_category'],
            'confidence_score': adjusted_confidence,
            'description_result': desc_result,
            'content_result': content_result,
            'method': method,
            'clip_duration': end_time - start_time,
            'disagreement': True
        }
    
    def get_category_suggestions(self, description: str, transcript_segment: str) -> List[Dict]:
        """
        Get suggested categories with confidence scores.
        
        Args:
            description: User's clip description
            transcript_segment: Relevant transcript content
            
        Returns:
            List of category suggestions sorted by confidence
        """
        desc_result = self.classify_by_description(description)
        content_result = self.classify_by_content(transcript_segment)
        
        # Combine scores from both methods
        combined_scores = {}
        
        # Add description scores
        for category, data in desc_result.get('all_scores', {}).items():
            combined_scores[category] = {
                'description_score': data['score'],
                'content_score': 0.0,
                'combined_score': data['score'] * 0.6  # Weight description slightly less
            }
        
        # Add content scores
        for category, data in content_result.get('all_scores', {}).items():
            if category in combined_scores:
                combined_scores[category]['content_score'] = data['score']
                combined_scores[category]['combined_score'] += data['score'] * 0.8
            else:
                combined_scores[category] = {
                    'description_score': 0.0,
                    'content_score': data['score'],
                    'combined_score': data['score'] * 0.8
                }
        
        # Convert to suggestions list
        suggestions = []
        for category, scores in combined_scores.items():
            confidence = min(scores['combined_score'] / 10.0, 1.0)
            suggestions.append({
                'category': category,
                'confidence': confidence,
                'description_score': scores['description_score'],
                'content_score': scores['content_score']
            })
        
        # Sort by confidence and return top suggestions
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:3]  # Return top 3 suggestions
    
    def get_category_info(self, category: str) -> Dict:
        """
        Get information about a specific category.
        
        Args:
            category: Category name
            
        Returns:
            Dictionary with category information
        """
        if category not in self.categories:
            return {
                'category': category,
                'exists': False,
                'keywords': [],
                'description': 'Unknown category'
            }
        
        descriptions = {
            'inflation': 'Content related to inflation, price levels, and cost analysis',
            'fed': 'Federal Reserve policy, interest rates, and monetary decisions',
            'markets': 'Stock market analysis, trading, and investment content',
            'gdp': 'Economic growth, GDP data, and productivity discussions',
            'employment': 'Jobs market, unemployment, and labor statistics',
            'banking': 'Banking sector, credit markets, and financial institutions',
            'crypto': 'Cryptocurrency, digital assets, and blockchain regulation',
            'housing': 'Real estate market, housing prices, and mortgage trends',
            'international': 'Global economics, trade, and international markets',
            'general': 'Uncategorized economic content'
        }
        
        return {
            'category': category,
            'exists': True,
            'keywords': self.categories[category],
            'description': descriptions.get(category, 'Economic content category'),
            'keyword_count': len(self.categories[category])
        }
    
    def validate_classification(self, category: str, description: str, 
                              transcript_segment: str) -> Dict:
        """
        Validate if a manual classification makes sense.
        
        Args:
            category: Proposed category
            description: User's description
            transcript_segment: Transcript content
            
        Returns:
            Validation results
        """
        if category not in self.categories:
            return {
                'valid': False,
                'reason': f'Category "{category}" does not exist',
                'confidence': 0.0
            }
        
        # Run automatic classification
        auto_result = self.classify_combined(description, transcript_segment, 0, 60)
        
        if auto_result['primary_category'] == category:
            return {
                'valid': True,
                'reason': 'Manual classification matches automatic analysis',
                'confidence': auto_result['confidence_score'],
                'agreement': True
            }
        else:
            # Check if manual category appears in suggestions
            suggestions = self.get_category_suggestions(description, transcript_segment)
            manual_suggestion = next((s for s in suggestions if s['category'] == category), None)
            
            if manual_suggestion and manual_suggestion['confidence'] > 0.3:
                return {
                    'valid': True,
                    'reason': f'Manual category is a reasonable alternative (confidence: {manual_suggestion["confidence"]:.2f})',
                    'confidence': manual_suggestion['confidence'],
                    'agreement': False,
                    'auto_category': auto_result['primary_category']
                }
            else:
                return {
                    'valid': False,
                    'reason': f'Manual category does not match content. Suggested: {auto_result["primary_category"]}',
                    'confidence': 0.0,
                    'agreement': False,
                    'auto_category': auto_result['primary_category']
                }


# Global instance for easy access
topic_classifier = TopicClassifier()
