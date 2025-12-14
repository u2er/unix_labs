#include <iostream>
#include <filesystem>
#include <fstream>
#include <vector>
#include <string>
#include <map>
#include <iomanip>
#include <sstream>

namespace fs = std::filesystem;

std::string calculate_file_hash(const fs::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        return "";
    }

    const uint64_t FNV_prime = 1099511628211u;
    const uint64_t offset_basis = 14695981039346656037u;

    uint64_t hash = offset_basis;
    char buffer[4096];

    while (file.read(buffer, sizeof(buffer)) || file.gcount() > 0) {
        std::streamsize bytes_read = file.gcount();
        for (std::streamsize i = 0; i < bytes_read; ++i) {
            hash ^= static_cast<uint8_t>(buffer[i]);
            hash *= FNV_prime;
        }
        if (file.eof()) break;
    }

    std::stringstream ss;
    ss << std::hex << std::setw(16) << std::setfill('0') << hash;
    return ss.str();
}

int main(int argc, char* argv[]) {
    std::setlocale(LC_ALL, "");

    fs::path targetDir = argv[1];

    try {
        if (!fs::exists(targetDir) || !fs::is_directory(targetDir)) {
            std::cerr << "Ошибка: Указанный путь не существует или не является каталогом." << std::endl;
            return 1;
        }
    } catch (const fs::filesystem_error& e) {
        std::cerr << "Ошибка доступа к пути: " << e.what() << std::endl;
        return 1;
    }

    std::map<std::string, fs::path> unique_files;
    
    size_t processed_files = 0;
    size_t duplicates_found = 0;
    size_t errors = 0;

    std::cout << "Сканирование: " << targetDir << " ...\n" << std::endl;

    try {
        for (const auto& entry : fs::recursive_directory_iterator(targetDir)) {
            try {
                if (entry.is_regular_file()) {
                    processed_files++;
                    fs::path current_path = entry.path();
                    
                    std::string hash = calculate_file_hash(current_path);
                    
                    if (hash.empty()) {
                        // Пустой хэш может быть у пустого файла или если файл заблокирован.
                        // Для надежности проверим размер. Если >0 и хэш пуст - ошибка чтения.
                        if (fs::file_size(current_path) > 0) {
                             std::cerr << "[!] Не удалось прочитать файл: " << current_path << std::endl;
                             errors++;
                             continue;
                        }
                    }

                    if (unique_files.find(hash) != unique_files.end()) {
                        fs::path original_path = unique_files[hash];

                        if (fs::equivalent(current_path, original_path)) {
                            continue; 
                        }

                        duplicates_found++;
                        std::cout << "[ДУБЛИКАТ] " << current_path.filename() 
                                  << " == " << original_path.filename() << std::endl;
                        
                        try {
                            fs::remove(current_path);
                            fs::create_hard_link(original_path, current_path);
                            std::cout << " -> Заменен на жёсткую ссылку." << std::endl;
                        } catch (const fs::filesystem_error& e) {
                            std::cerr << " -> Ошибка при создании ссылки: " << e.what() << std::endl;
                            errors++;
                        }

                    } else {
                        unique_files[hash] = current_path;
                    }
                }
            } catch (const std::exception& e) {
                std::cerr << "Ошибка обработки файла: " << e.what() << std::endl;
                errors++;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "Ошибка при обходе: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "\n--- Итоги ---" << std::endl;
    std::cout << "Всего обработано файлов: " << processed_files << std::endl;
    std::cout << "Заменено на жёсткие ссылки: " << duplicates_found << std::endl;
    std::cout << "Ошибок: " << errors << std::endl;

    return 0;
}