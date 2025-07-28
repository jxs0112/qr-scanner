#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFC标签写入工具
用于快速配置10页文档的NFC标签
"""

import time
import nfc
import nfc.ndef

def write_page_tag(page_number, total_pages=10):
    """
    写入页面标签
    
    Args:
        page_number (int): 页码
        total_pages (int): 总页数
    """
    print(f"\n📝 准备写入第 {page_number} 页标签")
    print(f"请将标签 #{page_number} 靠近NFC读卡器...")
    
    clf = nfc.ContactlessFrontend()
    if not clf:
        print("❌ 无法连接NFC设备")
        return False
    
    success = False
    
    def write_tag(tag):
        nonlocal success
        try:
            if tag.ndef:
                # 创建文本记录
                text_content = f"第{page_number}页"
                text_record = nfc.ndef.TextRecord(text_content, "zh-CN")
                
                # 创建URI记录作为备用
                uri_content = f"http://localhost/?page={page_number}&total={total_pages}"
                uri_record = nfc.ndef.UriRecord(uri_content)
                
                # 写入标签
                tag.ndef.records = [text_record, uri_record]
                
                print(f"✅ 第 {page_number} 页标签写入成功!")
                print(f"   标签ID: {tag.identifier.hex()}")
                print(f"   内容: {text_content}")
                print(f"   URI: {uri_content}")
                
                success = True
                return True
            else:
                print(f"❌ 标签不支持NDEF格式")
                return False
                
        except Exception as e:
            print(f"❌ 写入失败: {e}")
            return False
    
    try:
        # 等待标签
        tag = clf.connect(rdwr={'on-connect': write_tag})
        
        if not success:
            print(f"❌ 第 {page_number} 页标签写入失败")
            
    except Exception as e:
        print(f"❌ NFC连接错误: {e}")
    finally:
        clf.close()
    
    return success

def batch_write_tags(total_pages=10):
    """
    批量写入标签
    
    Args:
        total_pages (int): 总页数
    """
    print(f"🏷️  NFC标签批量写入工具")
    print(f"准备为 {total_pages} 页文档配置标签")
    print(f"=" * 40)
    
    print(f"\n📋 写入计划:")
    for i in range(1, total_pages + 1):
        print(f"  标签 #{i}: 第{i}页")
    
    input("\n按 Enter 键开始写入...")
    
    success_count = 0
    failed_pages = []
    
    for page in range(1, total_pages + 1):
        print(f"\n⏳ 进度: {page}/{total_pages}")
        
        if write_page_tag(page, total_pages):
            success_count += 1
            input(f"✅ 第 {page} 页完成，请放置下一个标签后按 Enter...")
        else:
            failed_pages.append(page)
            retry = input(f"❌ 第 {page} 页失败，是否重试? (y/n): ").lower()
            if retry == 'y':
                if write_page_tag(page, total_pages):
                    success_count += 1
                    failed_pages.remove(page)
                    input(f"✅ 第 {page} 页重试成功，请放置下一个标签后按 Enter...")
                else:
                    input(f"❌ 第 {page} 页重试仍失败，按 Enter 继续...")
    
    # 显示结果
    print(f"\n🎉 批量写入完成!")
    print(f"成功: {success_count}/{total_pages} 个标签")
    
    if failed_pages:
        print(f"❌ 失败的页面: {failed_pages}")
        print(f"建议稍后重新写入这些标签")
    else:
        print(f"✅ 所有标签写入成功!")
    
    return success_count, failed_pages

def test_read_tag():
    """
    测试读取标签
    """
    print(f"\n🔍 NFC标签读取测试")
    print(f"请将标签靠近读卡器...")
    
    clf = nfc.ContactlessFrontend()
    if not clf:
        print("❌ 无法连接NFC设备")
        return
    
    def read_tag(tag):
        try:
            print(f"\n📱 检测到标签:")
            print(f"   标签ID: {tag.identifier.hex()}")
            print(f"   标签类型: {tag.type}")
            
            if tag.ndef and tag.ndef.records:
                print(f"   NDEF记录数: {len(tag.ndef.records)}")
                
                for i, record in enumerate(tag.ndef.records):
                    print(f"\n   记录 {i+1}:")
                    print(f"     类型: {record.type}")
                    
                    if record.type == 'urn:nfc:wkt:T':
                        try:
                            text = record.text
                            print(f"     文本: {text}")
                        except:
                            print(f"     文本: 无法解析")
                    
                    elif record.type == 'urn:nfc:wkt:U':
                        try:
                            uri = record.uri
                            print(f"     URI: {uri}")
                        except:
                            print(f"     URI: 无法解析")
            else:
                print(f"   无NDEF记录")
            
            return True
            
        except Exception as e:
            print(f"❌ 读取失败: {e}")
            return False
    
    try:
        tag = clf.connect(rdwr={'on-connect': read_tag})
    except Exception as e:
        print(f"❌ NFC连接错误: {e}")
    finally:
        clf.close()

def main():
    """
    主函数
    """
    import sys
    
    print("=== NFC标签写入工具 ===")
    print("快速配置分页导航标签")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("\n使用方法:")
            print("  python3 nfc_tag_writer.py [选项] [页数]")
            print("\n选项:")
            print("  --batch     批量写入所有标签")
            print("  --single N  写入单个标签(第N页)")
            print("  --test      测试读取标签")
            print("  --help      显示此帮助")
            print("\n参数:")
            print("  页数: 总页数 (默认: 10)")
            print("\n示例:")
            print("  python3 nfc_tag_writer.py --batch     # 批量写入10页")
            print("  python3 nfc_tag_writer.py --batch 15  # 批量写入15页")
            print("  python3 nfc_tag_writer.py --single 3  # 只写入第3页")
            print("  python3 nfc_tag_writer.py --test      # 测试读取")
            return
        
        elif sys.argv[1] == '--test':
            test_read_tag()
            return
        
        elif sys.argv[1] == '--batch':
            total_pages = 10
            if len(sys.argv) > 2:
                try:
                    total_pages = int(sys.argv[2])
                except ValueError:
                    print("❌ 无效的页数")
                    return
            
            batch_write_tags(total_pages)
            return
        
        elif sys.argv[1] == '--single':
            if len(sys.argv) < 3:
                print("❌ 请指定页码")
                return
            
            try:
                page_number = int(sys.argv[2])
                write_page_tag(page_number)
            except ValueError:
                print("❌ 无效的页码")
            return
    
    # 交互模式
    print("\n请选择操作:")
    print("1. 批量写入标签")
    print("2. 写入单个标签")
    print("3. 测试读取标签")
    print("4. 退出")
    
    try:
        choice = input("\n请选择 (1-4): ").strip()
        
        if choice == '1':
            total_pages = input("总页数 (默认10): ").strip()
            total_pages = int(total_pages) if total_pages else 10
            batch_write_tags(total_pages)
        
        elif choice == '2':
            page_number = int(input("页码: ").strip())
            write_page_tag(page_number)
        
        elif choice == '3':
            test_read_tag()
        
        elif choice == '4':
            print("退出")
        
        else:
            print("❌ 无效选择")
    
    except (ValueError, KeyboardInterrupt):
        print("\n程序中断")
    except Exception as e:
        print(f"❌ 程序错误: {e}")

if __name__ == "__main__":
    main() 