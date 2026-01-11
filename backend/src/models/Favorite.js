const mongoose = require('mongoose');

const favoriteSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true,
    index: true
  },
  
  productId: {
    type: String,
    required: true,
    index: true
  },
  
  productName: {
    type: String,
    required: true,
    trim: true
  },
  
  brandName: {
    type: String,
    required: true,
    trim: true
  },
  
  price: {
    type: Number,
    required: true,
    min: 0
  },
  
  originalPrice: {
    type: Number,
    min: 0
  },
  
  ingredients: {
    type: String,
    default: ''
  },
  
  similarity: {
    type: Number,
    min: 0,
    max: 1,
    default: 0
  },
  
  category: {
    type: String,
    default: 'Unknown'
  },
  
  productType: {
    type: String,
    default: 'unknown'
  },
  
  source: {
    type: String,
    enum: ['dupe_finder', 'scanner', 'manual'],
    default: 'dupe_finder'
  },
  
  addedAt: {
    type: Date,
    default: Date.now
  },
  
  notes: {
    type: String,
    default: ''
  },
  
  metadata: {
    type: Map,
    of: mongoose.Schema.Types.Mixed,
    default: {}
  }
}, {
  timestamps: true
});

// Index composé pour éviter les doublons
favoriteSchema.index({ userId: 1, productId: 1 }, { unique: true });

// Méthode pour calculer l'économie
favoriteSchema.virtual('savings').get(function() {
  if (this.originalPrice && this.originalPrice > this.price) {
    return this.originalPrice - this.price;
  }
  return 0;
});

favoriteSchema.virtual('savingsPercentage').get(function() {
  if (this.originalPrice && this.originalPrice > 0) {
    return ((this.originalPrice - this.price) / this.originalPrice * 100).toFixed(1);
  }
  return 0;
});

const Favorite = mongoose.model('Favorite', favoriteSchema);

module.exports = Favorite;