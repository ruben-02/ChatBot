# Use PHP 8.1 with Apache
FROM php:8.1-apache

# Copy the frontend code to Apache's document root
COPY ../frontend/ /var/www/html/

# Expose port 80
EXPOSE 80

# Start Apache in foreground
CMD ["apache2-foreground"]
