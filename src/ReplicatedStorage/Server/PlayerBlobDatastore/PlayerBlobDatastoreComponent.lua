-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:22 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.MissionInfo)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
require(game.ReplicatedStorage.PlayerInfo.PremiumRewardsInfo)
require(game.ReplicatedStorage.PlayerInfo.GroupRewardsInfo)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.Mutex)
require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.Shared.GuildUtil)
require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.CooldownDelay)
local v65 = {
    ["SongShopDayInfo"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            local v66 = {}
            local v_u_67 = 0
            local v_u_68 = 0
            local v_u_69 = 0
            v66.get_sale_id = function(_) --[[ Name: get_sale_id ]] --[[ Line: 55 ]]
                --[[ Upvalues: (ref 1): v_u_67 ]]
                return v_u_67;
            end;
            v66.set_sale_id = function(p70, p71) --[[ Name: set_sale_id ]] --[[ Line: 56 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_67 ]]
                v_u_4:is_int(p71)
                v_u_67 = p71
                return p70;
            end;
            v66.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 57 ]]
                --[[ Upvalues: (ref 1): v_u_68 ]]
                return v_u_68;
            end;
            v66.set_count = function(p72, p73) --[[ Name: set_count ]] --[[ Line: 58 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_68 ]]
                v_u_4:is_int(p73)
                v_u_68 = p73
                return p72;
            end;
            v66.get_day_id = function(_) --[[ Name: get_day_id ]] --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): v_u_69 ]]
                return v_u_69;
            end;
            v66.set_day_id = function(p74, p75) --[[ Name: set_day_id ]] --[[ Line: 60 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_69 ]]
                v_u_4:is_int(p75)
                v_u_69 = p75
                return p74;
            end;
            v66.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 62 ]]
                --[[ Upvalues: (ref 1): v_u_67, (ref 2): v_u_68, (ref 3): v_u_69 ]]
                return {
                    ["SaleId"] = v_u_67,
                    ["Count"] = v_u_68,
                    ["DayID"] = v_u_69
                };
            end;
            return v66;
        end
    },
    ["GearShopDayInfo"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 81 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            local v78 = {}
            local v_u_79 = 0
            local v_u_80 = 0
            local v_u_81 = 0
            v78.get_sale_id = function(_) --[[ Name: get_sale_id ]] --[[ Line: 88 ]]
                --[[ Upvalues: (ref 1): v_u_79 ]]
                return v_u_79;
            end;
            v78.set_sale_id = function(p82, p83) --[[ Name: set_sale_id ]] --[[ Line: 89 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_79 ]]
                v_u_4:is_int(p83)
                v_u_79 = p83
                return p82;
            end;
            v78.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 90 ]]
                --[[ Upvalues: (ref 1): v_u_80 ]]
                return v_u_80;
            end;
            v78.set_count = function(p84, p85) --[[ Name: set_count ]] --[[ Line: 91 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_80 ]]
                v_u_4:is_int(p85)
                v_u_80 = p85
                return p84;
            end;
            v78.get_day_id = function(_) --[[ Name: get_day_id ]] --[[ Line: 92 ]]
                --[[ Upvalues: (ref 1): v_u_81 ]]
                return v_u_81;
            end;
            v78.set_day_id = function(p86, p87) --[[ Name: set_day_id ]] --[[ Line: 93 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_81 ]]
                v_u_4:is_int(p87)
                v_u_81 = p87
                return p86;
            end;
            v78.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 95 ]]
                --[[ Upvalues: (ref 1): v_u_79, (ref 2): v_u_80, (ref 3): v_u_81 ]]
                return {
                    ["SaleId"] = v_u_79,
                    ["Count"] = v_u_80,
                    ["DayID"] = v_u_81
                };
            end;
            return v78;
        end
    },
    ["DayMissionProgress"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 114 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            local v90 = {}
            local v_u_91 = 0
            local v_u_92 = 0
            local v_u_93 = false
            local v_u_94 = 0
            v90.get_mission_id = function(_) --[[ Name: get_mission_id ]] --[[ Line: 122 ]]
                --[[ Upvalues: (ref 1): v_u_91 ]]
                return v_u_91;
            end;
            v90.set_mission_id = function(p95, p96) --[[ Name: set_mission_id ]] --[[ Line: 123 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_91 ]]
                v_u_4:is_int(p96)
                v_u_91 = p96
                return p95;
            end;
            v90.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 124 ]]
                --[[ Upvalues: (ref 1): v_u_92 ]]
                return v_u_92;
            end;
            v90.set_count = function(p97, p98) --[[ Name: set_count ]] --[[ Line: 125 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_92 ]]
                v_u_4:is_int(p98)
                v_u_92 = p98
                return p97;
            end;
            v90.get_completed = function(_) --[[ Name: get_completed ]] --[[ Line: 126 ]]
                --[[ Upvalues: (ref 1): v_u_93 ]]
                return v_u_93;
            end;
            v90.set_completed = function(p99, p100) --[[ Name: set_completed ]] --[[ Line: 127 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_93 ]]
                v_u_4:is_bool(p100)
                v_u_93 = p100
                return p99;
            end;
            v90.get_day_id = function(_) --[[ Name: get_day_id ]] --[[ Line: 128 ]]
                --[[ Upvalues: (ref 1): v_u_94 ]]
                return v_u_94;
            end;
            v90.set_day_id = function(p101, p102) --[[ Name: set_day_id ]] --[[ Line: 129 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_94 ]]
                v_u_4:is_int(p102)
                v_u_94 = p102
                return p101;
            end;
            v90.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 131 ]]
                --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_92, (ref 3): v_u_93, (ref 4): v_u_94 ]]
                return {
                    ["MissionID"] = v_u_91,
                    ["Count"] = v_u_92,
                    ["Completed"] = v_u_93,
                    ["DayID"] = v_u_94
                };
            end;
            return v90;
        end
    },
    ["DailySection"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 160 ]]
            --[[ Upvalues: (copy 1): v_u_2, (copy 2): f_to_table_obj_list_to_table ]]
            local v108 = {}
            local v_u_109 = v_u_2:new()
            local v_u_110 = v_u_2:new()
            local v_u_111 = v_u_2:new()
            v108.get_song_shop_day_info = function(_) --[[ Name: get_song_shop_day_info ]] --[[ Line: 167 ]]
                --[[ Upvalues: (copy 1): v_u_109 ]]
                return v_u_109;
            end;
            v108.get_gear_shop_day_info = function(_) --[[ Name: get_gear_shop_day_info ]] --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_110 ]]
                return v_u_110;
            end;
            v108.get_day_mission_progress = function(_) --[[ Name: get_day_mission_progress ]] --[[ Line: 169 ]]
                --[[ Upvalues: (copy 1): v_u_111 ]]
                return v_u_111;
            end;
            v108.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 171 ]]
                --[[ Upvalues: (ref 1): f_to_table_obj_list_to_table, (copy 2): v_u_109, (copy 3): v_u_110, (copy 4): v_u_111 ]]
                return {
                    ["SongShopDayInfo"] = f_to_table_obj_list_to_table(v_u_109),
                    ["GearShopDayInfo"] = f_to_table_obj_list_to_table(v_u_110),
                    ["DayMissionProgress"] = f_to_table_obj_list_to_table(v_u_111)
                };
            end;
            return v108;
        end,
        ["clear_playerblob"] = function(_, p112) --[[ Name: clear_playerblob ]] --[[ Line: 229 ]]
            p112.SongShopDayInfo = {}
            p112.GearShopDayInfo = {}
            p112.DayMissionProgress = {}
        end,
        ["write_section_to_playerblob"] = function(_, p113, p114) --[[ Name: write_section_to_playerblob ]] --[[ Line: 235 ]]
            --[[ Upvalues: (copy 1): f_to_table_obj_list_to_table ]]
            p114.SongShopDayInfo = f_to_table_obj_list_to_table(p113:get_song_shop_day_info())
            p114.GearShopDayInfo = f_to_table_obj_list_to_table(p113:get_gear_shop_day_info())
            p114.DayMissionProgress = f_to_table_obj_list_to_table(p113:get_day_mission_progress())
        end
    },
    ["WeekMissionProgress"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 244 ]]
            --[[ Upvalues: (copy 1): v_u_4 ]]
            local v131 = {}
            local v_u_132 = 0
            local v_u_133 = 0
            local v_u_134 = false
            local v_u_135 = 0
            v131.get_mission_id = function(_) --[[ Name: get_mission_id ]] --[[ Line: 252 ]]
                --[[ Upvalues: (ref 1): v_u_132 ]]
                return v_u_132;
            end;
            v131.set_mission_id = function(p136, p137) --[[ Name: set_mission_id ]] --[[ Line: 253 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_132 ]]
                v_u_4:is_int(p137)
                v_u_132 = p137
                return p136;
            end;
            v131.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 254 ]]
                --[[ Upvalues: (ref 1): v_u_133 ]]
                return v_u_133;
            end;
            v131.set_count = function(p138, p139) --[[ Name: set_count ]] --[[ Line: 255 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_133 ]]
                v_u_4:is_int(p139)
                v_u_133 = p139
                return p138;
            end;
            v131.get_completed = function(_) --[[ Name: get_completed ]] --[[ Line: 256 ]]
                --[[ Upvalues: (ref 1): v_u_134 ]]
                return v_u_134;
            end;
            v131.set_completed = function(p140, p141) --[[ Name: set_completed ]] --[[ Line: 257 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_134 ]]
                v_u_4:is_bool(p141)
                v_u_134 = p141
                return p140;
            end;
            v131.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 258 ]]
                --[[ Upvalues: (ref 1): v_u_135 ]]
                return v_u_135;
            end;
            v131.set_week_id = function(p142, p143) --[[ Name: set_week_id ]] --[[ Line: 259 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_135 ]]
                v_u_4:is_int(p143)
                v_u_135 = p143
                return p142;
            end;
            v131.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 261 ]]
                --[[ Upvalues: (ref 1): v_u_132, (ref 2): v_u_133, (ref 3): v_u_134, (ref 4): v_u_135 ]]
                return {
                    ["MissionID"] = v_u_132,
                    ["Count"] = v_u_133,
                    ["Completed"] = v_u_134,
                    ["WeekID"] = v_u_135
                };
            end;
            return v131;
        end
    },
    ["WeeklySection"] = {
        ["new"] = function(_) --[[ Name: new ]] --[[ Line: 283 ]]
            --[[ Upvalues: (copy 1): v_u_2, (copy 2): f_to_table_obj_list_to_table ]]
            local v146 = {}
            local v_u_147 = v_u_2:new()
            v146.get_week_mission_progress = function(_) --[[ Name: get_week_mission_progress ]] --[[ Line: 288 ]]
                --[[ Upvalues: (copy 1): v_u_147 ]]
                return v_u_147;
            end;
            v146.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 290 ]]
                --[[ Upvalues: (ref 1): f_to_table_obj_list_to_table, (copy 2): v_u_147 ]]
                return {
                    ["WeekMissionProgress"] = f_to_table_obj_list_to_table(v_u_147)
                };
            end;
            return v146;
        end,
        ["has_changes"] = function(_, p148, p149) --[[ Name: has_changes ]] --[[ Line: 307 ]]
            --[[ Upvalues: (copy 1): f_to_table_obj_list_has_changes ]]
            return f_to_table_obj_list_has_changes(p148:get_week_mission_progress(), p149:get_week_mission_progress()) and true or false;
        end,
        ["clear_playerblob"] = function(_, p150) --[[ Name: clear_playerblob ]] --[[ Line: 318 ]]
            p150.WeekMissionProgress = {}
        end,
        ["write_section_to_playerblob"] = function(_, p151, p152) --[[ Name: write_section_to_playerblob ]] --[[ Line: 322 ]]
            --[[ Upvalues: (copy 1): f_to_table_obj_list_to_table ]]
            p152.WeekMissionProgress = f_to_table_obj_list_to_table(p151:get_week_mission_progress())
        end
    }
}
local v_u_76 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 48 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v66 = {}
        local v_u_67 = 0
        local v_u_68 = 0
        local v_u_69 = 0
        v66.get_sale_id = function(_) --[[ Name: get_sale_id ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_67 ]]
            return v_u_67;
        end;
        v66.set_sale_id = function(p70, p71) --[[ Name: set_sale_id ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_67 ]]
            v_u_4:is_int(p71)
            v_u_67 = p71
            return p70;
        end;
        v66.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_68 ]]
            return v_u_68;
        end;
        v66.set_count = function(p72, p73) --[[ Name: set_count ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_68 ]]
            v_u_4:is_int(p73)
            v_u_68 = p73
            return p72;
        end;
        v66.get_day_id = function(_) --[[ Name: get_day_id ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_69 ]]
            return v_u_69;
        end;
        v66.set_day_id = function(p74, p75) --[[ Name: set_day_id ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_69 ]]
            v_u_4:is_int(p75)
            v_u_69 = p75
            return p74;
        end;
        v66.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_67, (ref 2): v_u_68, (ref 3): v_u_69 ]]
            return {
                ["SaleId"] = v_u_67,
                ["Count"] = v_u_68,
                ["DayID"] = v_u_69
            };
        end;
        return v66;
    end
}
v_u_76.from_table = function(_, p77) --[[ Name: from_table ]] --[[ Line: 72 ]]
    --[[ Upvalues: (copy 1): v_u_76 ]]
    return v_u_76:new():set_sale_id(p77.SaleId):set_count(p77.Count):set_day_id(p77.DayID);
end;
local v_u_88 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 81 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v78 = {}
        local v_u_79 = 0
        local v_u_80 = 0
        local v_u_81 = 0
        v78.get_sale_id = function(_) --[[ Name: get_sale_id ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_79 ]]
            return v_u_79;
        end;
        v78.set_sale_id = function(p82, p83) --[[ Name: set_sale_id ]] --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_79 ]]
            v_u_4:is_int(p83)
            v_u_79 = p83
            return p82;
        end;
        v78.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): v_u_80 ]]
            return v_u_80;
        end;
        v78.set_count = function(p84, p85) --[[ Name: set_count ]] --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_80 ]]
            v_u_4:is_int(p85)
            v_u_80 = p85
            return p84;
        end;
        v78.get_day_id = function(_) --[[ Name: get_day_id ]] --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): v_u_81 ]]
            return v_u_81;
        end;
        v78.set_day_id = function(p86, p87) --[[ Name: set_day_id ]] --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_81 ]]
            v_u_4:is_int(p87)
            v_u_81 = p87
            return p86;
        end;
        v78.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 95 ]]
            --[[ Upvalues: (ref 1): v_u_79, (ref 2): v_u_80, (ref 3): v_u_81 ]]
            return {
                ["SaleId"] = v_u_79,
                ["Count"] = v_u_80,
                ["DayID"] = v_u_81
            };
        end;
        return v78;
    end
}
v_u_88.from_table = function(_, p89) --[[ Name: from_table ]] --[[ Line: 105 ]]
    --[[ Upvalues: (copy 1): v_u_88 ]]
    return v_u_88:new():set_sale_id(p89.SaleId):set_count(p89.Count):set_day_id(p89.DayID);
end;
local v_u_103 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 114 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v90 = {}
        local v_u_91 = 0
        local v_u_92 = 0
        local v_u_93 = false
        local v_u_94 = 0
        v90.get_mission_id = function(_) --[[ Name: get_mission_id ]] --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): v_u_91 ]]
            return v_u_91;
        end;
        v90.set_mission_id = function(p95, p96) --[[ Name: set_mission_id ]] --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_91 ]]
            v_u_4:is_int(p96)
            v_u_91 = p96
            return p95;
        end;
        v90.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 124 ]]
            --[[ Upvalues: (ref 1): v_u_92 ]]
            return v_u_92;
        end;
        v90.set_count = function(p97, p98) --[[ Name: set_count ]] --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_92 ]]
            v_u_4:is_int(p98)
            v_u_92 = p98
            return p97;
        end;
        v90.get_completed = function(_) --[[ Name: get_completed ]] --[[ Line: 126 ]]
            --[[ Upvalues: (ref 1): v_u_93 ]]
            return v_u_93;
        end;
        v90.set_completed = function(p99, p100) --[[ Name: set_completed ]] --[[ Line: 127 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_93 ]]
            v_u_4:is_bool(p100)
            v_u_93 = p100
            return p99;
        end;
        v90.get_day_id = function(_) --[[ Name: get_day_id ]] --[[ Line: 128 ]]
            --[[ Upvalues: (ref 1): v_u_94 ]]
            return v_u_94;
        end;
        v90.set_day_id = function(p101, p102) --[[ Name: set_day_id ]] --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_94 ]]
            v_u_4:is_int(p102)
            v_u_94 = p102
            return p101;
        end;
        v90.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_92, (ref 3): v_u_93, (ref 4): v_u_94 ]]
            return {
                ["MissionID"] = v_u_91,
                ["Count"] = v_u_92,
                ["Completed"] = v_u_93,
                ["DayID"] = v_u_94
            };
        end;
        return v90;
    end
}
v_u_103.from_table = function(_, p104) --[[ Name: from_table ]] --[[ Line: 142 ]]
    --[[ Upvalues: (copy 1): v_u_103 ]]
    return v_u_103:new():set_mission_id(p104.MissionID):set_count(p104.Count):set_completed(p104.Completed):set_day_id(p104.DayID);
end;
local function f_to_table_obj_list_to_table(p105) --[[ Name: to_table_obj_list_to_table ]] --[[ Line: 150 ]]
    local v106 = {}
    for _, v107 in p105:key_itr() do
        table.insert(v106, v107:to_table())
    end;
    return v106;
end;
local v_u_115 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 160 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): f_to_table_obj_list_to_table ]]
        local v108 = {}
        local v_u_109 = v_u_2:new()
        local v_u_110 = v_u_2:new()
        local v_u_111 = v_u_2:new()
        v108.get_song_shop_day_info = function(_) --[[ Name: get_song_shop_day_info ]] --[[ Line: 167 ]]
            --[[ Upvalues: (copy 1): v_u_109 ]]
            return v_u_109;
        end;
        v108.get_gear_shop_day_info = function(_) --[[ Name: get_gear_shop_day_info ]] --[[ Line: 168 ]]
            --[[ Upvalues: (copy 1): v_u_110 ]]
            return v_u_110;
        end;
        v108.get_day_mission_progress = function(_) --[[ Name: get_day_mission_progress ]] --[[ Line: 169 ]]
            --[[ Upvalues: (copy 1): v_u_111 ]]
            return v_u_111;
        end;
        v108.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 171 ]]
            --[[ Upvalues: (ref 1): f_to_table_obj_list_to_table, (copy 2): v_u_109, (copy 3): v_u_110, (copy 4): v_u_111 ]]
            return {
                ["SongShopDayInfo"] = f_to_table_obj_list_to_table(v_u_109),
                ["GearShopDayInfo"] = f_to_table_obj_list_to_table(v_u_110),
                ["DayMissionProgress"] = f_to_table_obj_list_to_table(v_u_111)
            };
        end;
        return v108;
    end,
    ["clear_playerblob"] = function(_, p112) --[[ Name: clear_playerblob ]] --[[ Line: 229 ]]
        p112.SongShopDayInfo = {}
        p112.GearShopDayInfo = {}
        p112.DayMissionProgress = {}
    end,
    ["write_section_to_playerblob"] = function(_, p113, p114) --[[ Name: write_section_to_playerblob ]] --[[ Line: 235 ]]
        --[[ Upvalues: (copy 1): f_to_table_obj_list_to_table ]]
        p114.SongShopDayInfo = f_to_table_obj_list_to_table(p113:get_song_shop_day_info())
        p114.GearShopDayInfo = f_to_table_obj_list_to_table(p113:get_gear_shop_day_info())
        p114.DayMissionProgress = f_to_table_obj_list_to_table(p113:get_day_mission_progress())
    end
}
v_u_115.from_table = function(_, p116) --[[ Name: from_table ]] --[[ Line: 182 ]]
    --[[ Upvalues: (copy 1): v_u_115, (copy 2): v_u_76, (copy 3): v_u_88, (copy 4): v_u_103 ]]
    local v117 = v_u_115:new()
    for _, v118 in pairs(p116.SongShopDayInfo) do
        v117:get_song_shop_day_info():push_back(v_u_76:from_table(v118))
    end;
    for _, v119 in pairs(p116.GearShopDayInfo) do
        v117:get_gear_shop_day_info():push_back(v_u_88:from_table(v119))
    end;
    for _, v120 in pairs(p116.DayMissionProgress) do
        v117:get_day_mission_progress():push_back(v_u_103:from_table(v120))
    end;
    return v117;
end;
local function f_to_table_obj_list_has_changes(p121, p122) --[[ Name: to_table_obj_list_has_changes ]] --[[ Line: 196 ]]
    if p121:count() ~= p122:count() then
        return true;
    end;
    for v123 = 1, p121:count() do
        local v124 = p121:get(v123):to_table()
        local v125 = p122:get(v123):to_table()
        for v126, v127 in pairs(v124) do
            if v125[v126] ~= v127 then
                return true;
            end;
        end;
    end;
    return false;
end;
v_u_115.has_changes = function(_, p128, p129) --[[ Name: has_changes ]] --[[ Line: 212 ]]
    --[[ Upvalues: (copy 1): f_to_table_obj_list_has_changes ]]
    return f_to_table_obj_list_has_changes(p128:get_song_shop_day_info(), p129:get_song_shop_day_info()) and true or (f_to_table_obj_list_has_changes(p128:get_gear_shop_day_info(), p129:get_gear_shop_day_info()) and true or (f_to_table_obj_list_has_changes(p128:get_day_mission_progress(), p129:get_day_mission_progress()) and true or false));
end;
v_u_115.create_from_playerblob = function(_, p130) --[[ Name: create_from_playerblob ]] --[[ Line: 225 ]]
    --[[ Upvalues: (copy 1): v_u_115 ]]
    return v_u_115:from_table(p130);
end;
local v_u_144 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 244 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v131 = {}
        local v_u_132 = 0
        local v_u_133 = 0
        local v_u_134 = false
        local v_u_135 = 0
        v131.get_mission_id = function(_) --[[ Name: get_mission_id ]] --[[ Line: 252 ]]
            --[[ Upvalues: (ref 1): v_u_132 ]]
            return v_u_132;
        end;
        v131.set_mission_id = function(p136, p137) --[[ Name: set_mission_id ]] --[[ Line: 253 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_132 ]]
            v_u_4:is_int(p137)
            v_u_132 = p137
            return p136;
        end;
        v131.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 254 ]]
            --[[ Upvalues: (ref 1): v_u_133 ]]
            return v_u_133;
        end;
        v131.set_count = function(p138, p139) --[[ Name: set_count ]] --[[ Line: 255 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_133 ]]
            v_u_4:is_int(p139)
            v_u_133 = p139
            return p138;
        end;
        v131.get_completed = function(_) --[[ Name: get_completed ]] --[[ Line: 256 ]]
            --[[ Upvalues: (ref 1): v_u_134 ]]
            return v_u_134;
        end;
        v131.set_completed = function(p140, p141) --[[ Name: set_completed ]] --[[ Line: 257 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_134 ]]
            v_u_4:is_bool(p141)
            v_u_134 = p141
            return p140;
        end;
        v131.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 258 ]]
            --[[ Upvalues: (ref 1): v_u_135 ]]
            return v_u_135;
        end;
        v131.set_week_id = function(p142, p143) --[[ Name: set_week_id ]] --[[ Line: 259 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_135 ]]
            v_u_4:is_int(p143)
            v_u_135 = p143
            return p142;
        end;
        v131.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 261 ]]
            --[[ Upvalues: (ref 1): v_u_132, (ref 2): v_u_133, (ref 3): v_u_134, (ref 4): v_u_135 ]]
            return {
                ["MissionID"] = v_u_132,
                ["Count"] = v_u_133,
                ["Completed"] = v_u_134,
                ["WeekID"] = v_u_135
            };
        end;
        return v131;
    end
}
v_u_144.from_table = function(_, p145) --[[ Name: from_table ]] --[[ Line: 272 ]]
    --[[ Upvalues: (copy 1): v_u_144 ]]
    return v_u_144:new():set_mission_id(p145.MissionID):set_count(p145.Count):set_completed(p145.Completed):set_week_id(p145.WeekID);
end;
local v_u_153 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 283 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): f_to_table_obj_list_to_table ]]
        local v146 = {}
        local v_u_147 = v_u_2:new()
        v146.get_week_mission_progress = function(_) --[[ Name: get_week_mission_progress ]] --[[ Line: 288 ]]
            --[[ Upvalues: (copy 1): v_u_147 ]]
            return v_u_147;
        end;
        v146.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 290 ]]
            --[[ Upvalues: (ref 1): f_to_table_obj_list_to_table, (copy 2): v_u_147 ]]
            return {
                ["WeekMissionProgress"] = f_to_table_obj_list_to_table(v_u_147)
            };
        end;
        return v146;
    end,
    ["has_changes"] = function(_, p148, p149) --[[ Name: has_changes ]] --[[ Line: 307 ]]
        --[[ Upvalues: (copy 1): f_to_table_obj_list_has_changes ]]
        return f_to_table_obj_list_has_changes(p148:get_week_mission_progress(), p149:get_week_mission_progress()) and true or false;
    end,
    ["clear_playerblob"] = function(_, p150) --[[ Name: clear_playerblob ]] --[[ Line: 318 ]]
        p150.WeekMissionProgress = {}
    end,
    ["write_section_to_playerblob"] = function(_, p151, p152) --[[ Name: write_section_to_playerblob ]] --[[ Line: 322 ]]
        --[[ Upvalues: (copy 1): f_to_table_obj_list_to_table ]]
        p152.WeekMissionProgress = f_to_table_obj_list_to_table(p151:get_week_mission_progress())
    end
}
v_u_153.from_table = function(_, p154) --[[ Name: from_table ]] --[[ Line: 299 ]]
    --[[ Upvalues: (copy 1): v_u_153, (copy 2): v_u_144 ]]
    local v155 = v_u_153:new()
    for _, v156 in pairs(p154.WeekMissionProgress) do
        v155:get_week_mission_progress():push_back(v_u_144:from_table(v156))
    end;
    return v155;
end;
v_u_153.create_from_playerblob = function(_, p157) --[[ Name: create_from_playerblob ]] --[[ Line: 314 ]]
    --[[ Upvalues: (copy 1): v_u_153 ]]
    return v_u_153:from_table(p157);
end;
v65.debug_log_playerblob_daily_section_weekly_section = function(_, p158, p159, p160) --[[ Name: debug_log_playerblob_daily_section_weekly_section ]] --[[ Line: 326 ]]
    --[[ Upvalues: (copy 1): v_u_115, (copy 2): v_u_153, (copy 3): v_u_1, (copy 4): v_u_3 ]]
    local v161 = v_u_115:create_from_playerblob(p158)
    local v162 = v_u_153:create_from_playerblob(p158)
    local v163
    if v_u_115:has_changes(v161, p159) then
        v_u_1:puts("[DEBUG] PlayerBlobDatastoreComponent:debug_log_playerblob_daily_section_weekly_section: playerblob daily section has changes")
        v_u_1:puts("[DEBUG] web playerblob:")
        v_u_1:puts(v_u_3:table_to_string(v161:to_table()))
        v_u_1:puts("datastore:")
        v_u_1:puts(v_u_3:table_to_string(p159:to_table()))
        v163 = true
    else
        v163 = false
    end;
    if v_u_153:has_changes(v162, p160) then
        v_u_1:puts("[DEBUG] PlayerBlobDatastoreComponent:debug_log_playerblob_daily_section_weekly_section: playerblob weekly section has changes")
        v_u_1:puts("[DEBUG] web playerblob:")
        v_u_1:puts(v_u_3:table_to_string(v162:to_table()))
        v_u_1:puts("[DEBUG] datastore:")
        v_u_1:puts(v_u_3:table_to_string(p160:to_table()))
        v163 = true
    end;
    if v163 == false then
        v_u_1:puts("PlayerBlobDatastoreComponent:debug_log_playerblob_daily_section_weekly_section: no changes")
    end;
end;
return v65;
