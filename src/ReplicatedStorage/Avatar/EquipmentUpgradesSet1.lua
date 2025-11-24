-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:18 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_1 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugConfig)
return {
    ["add_to_equipment_upgrade_database"] = function(_, p4) --[[ Name: add_to_equipment_upgrade_database ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        p4:add_equipment_upgrade(1, ((function() --[[ Line: 13 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v5 = v_u_1:new()
            v5.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 15 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Chill Points+" or "NoteSpeed+";
            end;
            v5.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 22 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorBlue] = 3
                } or {
                    [v_u_2.Type.NoteSpeed] = 2
                };
            end;
            v5.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 33 ]]
                return 5;
            end;
            v5.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 34 ]]
                return { 2, 1 };
            end;
            v5.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 35 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310337" or "rbxassetid://2177386338";
            end;
            return v5;
        end)()))
        p4:add_equipment_upgrade(2, ((function() --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v6 = v_u_1:new()
            v6.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 47 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Vibe Points+" or "NoteSpeed++";
            end;
            v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 54 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorGreen] = 3
                } or {
                    [v_u_2.Type.NoteSpeed] = 5
                };
            end;
            v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 65 ]]
                return 5;
            end;
            v6.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 66 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [5] = 2,
                    [6] = 1
                } or {
                    [18] = 1,
                    [2] = 1
                };
            end;
            v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 73 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310484" or "rbxassetid://2177386512";
            end;
            return v6;
        end)()))
        p4:add_equipment_upgrade(3, ((function() --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v7 = v_u_1:new()
            v7.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 85 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Flow Points+" or "NoteSpeed+++";
            end;
            v7.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 92 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorPurple] = 3
                } or {
                    [v_u_2.Type.NoteSpeed] = 10
                };
            end;
            v7.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 103 ]]
                return 5;
            end;
            v7.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 104 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [13] = 2,
                    [14] = 1
                } or {
                    [19] = 1,
                    [3] = 1
                };
            end;
            v7.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310692" or "rbxassetid://2177386693";
            end;
            return v7;
        end)()))
        p4:add_equipment_upgrade(4, ((function() --[[ Line: 121 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v8 = v_u_1:new()
            v8.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 123 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Rush Points+" or "NoteSpeed-";
            end;
            v8.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 130 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorRed] = 3
                } or {
                    [v_u_2.Type.NoteSpeed] = -2
                };
            end;
            v8.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 141 ]]
                return 5;
            end;
            v8.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 142 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [17] = 2,
                    [18] = 1
                } or {
                    [13] = 1,
                    [5] = 2
                };
            end;
            v8.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 149 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310807" or "rbxassetid://2177386985";
            end;
            return v8;
        end)()))
        p4:add_equipment_upgrade(5, ((function() --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v9 = v_u_1:new()
            v9.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 161 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Beat Points+" or "NoteSpeed--";
            end;
            v9.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 168 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorOrange] = 3
                } or {
                    [v_u_2.Type.NoteSpeed] = -5
                };
            end;
            v9.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 179 ]]
                return 5;
            end;
            v9.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 180 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [9] = 2,
                    [10] = 1
                } or {
                    [14] = 1,
                    [6] = 1
                };
            end;
            v9.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 187 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310162" or "rbxassetid://2177387174";
            end;
            return v9;
        end)()))
        p4:add_equipment_upgrade(6, ((function() --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v10 = v_u_1:new()
            v10.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 199 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Chill Points++" or "NoteSpeed---";
            end;
            v10.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 206 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorBlue] = 6
                } or {
                    [v_u_2.Type.NoteSpeed] = -10
                };
            end;
            v10.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 217 ]]
                return 10;
            end;
            v10.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 218 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [4] = 1
                } or {
                    [15] = 1,
                    [7] = 1
                };
            end;
            v10.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 225 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310616" or "rbxassetid://2177387372";
            end;
            return v10;
        end)()))
        p4:add_equipment_upgrade(7, ((function() --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v11 = v_u_1:new()
            v11.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 237 ]]
                return "PerfectTime+";
            end;
            v11.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 238 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorBlue] = 1,
                    [v_u_2.Type.PerfectTime] = 1,
                    [v_u_2.Type.PerfectPoints] = -1
                } or {
                    [v_u_2.Type.PerfectTime] = 1,
                    [v_u_2.Type.PerfectPoints] = -1
                };
            end;
            v11.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 252 ]]
                return 5;
            end;
            v11.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 253 ]]
                return {
                    [3] = 1,
                    [2] = 1
                };
            end;
            v11.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 254 ]]
                return "rbxassetid://2177377262";
            end;
            return v11;
        end)()))
        p4:add_equipment_upgrade(8, ((function() --[[ Line: 258 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v12 = v_u_1:new()
            v12.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 260 ]]
                return "PerfectTime++";
            end;
            v12.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 261 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorBlue] = 3,
                    [v_u_2.Type.PerfectTime] = 2,
                    [v_u_2.Type.ComboMultiplier] = -2
                } or {
                    [v_u_2.Type.PerfectTime] = 2,
                    [v_u_2.Type.ComboMultiplier] = -2
                };
            end;
            v12.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 275 ]]
                return 10;
            end;
            v12.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 276 ]]
                return {
                    [4] = 1
                };
            end;
            v12.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 277 ]]
                return "rbxassetid://2177378670";
            end;
            return v12;
        end)()))
        p4:add_equipment_upgrade(9, ((function() --[[ Line: 281 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v13 = v_u_1:new()
            v13.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 283 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Vibe Points++" or "ComboThreshold+";
            end;
            v13.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 290 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorGreen] = 6
                } or {
                    [v_u_2.Type.ComboThreshold] = 2
                };
            end;
            v13.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 301 ]]
                return 10;
            end;
            v13.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 302 ]]
                return {
                    [8] = 1
                };
            end;
            v13.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 303 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310545" or "rbxassetid://2177382556";
            end;
            return v13;
        end)()))
        p4:add_equipment_upgrade(10, ((function() --[[ Line: 313 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v14 = v_u_1:new()
            v14.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 315 ]]
                return "ComboMultiplier+";
            end;
            v14.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 316 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorPurple] = 1,
                    [v_u_2.Type.ComboMultiplier] = 1
                } or {
                    [v_u_2.Type.ComboMultiplier] = 1
                };
            end;
            v14.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 328 ]]
                return 5;
            end;
            v14.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 329 ]]
                return {
                    [15] = 1,
                    [14] = 1
                };
            end;
            v14.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 330 ]]
                return "rbxassetid://2177383417";
            end;
            return v14;
        end)()))
        p4:add_equipment_upgrade(11, ((function() --[[ Line: 334 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v15 = v_u_1:new()
            v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 336 ]]
                return "ComboMultiplier++";
            end;
            v15.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 337 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorPurple] = 3,
                    [v_u_2.Type.ComboMultiplier] = 2
                } or {
                    [v_u_2.Type.ComboMultiplier] = 2,
                    [v_u_2.Type.ComboBreakMultiplier] = -1
                };
            end;
            v15.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 350 ]]
                return 10;
            end;
            v15.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 351 ]]
                return {
                    [16] = 1
                };
            end;
            v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 352 ]]
                return "rbxassetid://2177383643";
            end;
            return v15;
        end)()))
        p4:add_equipment_upgrade(12, ((function() --[[ Line: 356 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v16 = v_u_1:new()
            v16.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 358 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Flow Points++" or "ComboBreakMultiplier+";
            end;
            v16.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 365 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorPurple] = 6
                } or {
                    [v_u_2.Type.ComboBreakMultiplier] = 2
                };
            end;
            v16.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 376 ]]
                return 10;
            end;
            v16.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 377 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [16] = 1
                } or {
                    [14] = 1,
                    [7] = 1
                };
            end;
            v16.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 384 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310750" or "rbxassetid://2177383160";
            end;
            return v16;
        end)()))
        p4:add_equipment_upgrade(13, ((function() --[[ Line: 394 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v17 = v_u_1:new()
            v17.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 396 ]]
                return "FeverFillRate+";
            end;
            v17.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 397 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorGreen] = 1,
                    [v_u_2.Type.FeverFillRate] = 1
                } or {
                    [v_u_2.Type.FeverFillRate] = 1
                };
            end;
            v17.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 409 ]]
                return 5;
            end;
            v17.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 410 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [6] = 1,
                    [7] = 1
                } or {
                    [3] = 1,
                    [11] = 1
                };
            end;
            v17.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 417 ]]
                return "rbxassetid://5682119938";
            end;
            return v17;
        end)()))
        p4:add_equipment_upgrade(14, ((function() --[[ Line: 421 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v18 = v_u_1:new()
            v18.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 423 ]]
                return "FeverFillRate++";
            end;
            v18.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 424 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorGreen] = 3,
                    [v_u_2.Type.FeverFillRate] = 3
                } or {
                    [v_u_2.Type.FeverFillRate] = 3,
                    [v_u_2.Type.FeverTime] = -1
                };
            end;
            v18.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 437 ]]
                return 10;
            end;
            v18.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 438 ]]
                return {
                    [8] = 1
                };
            end;
            v18.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 439 ]]
                return "rbxassetid://5682119876";
            end;
            return v18;
        end)()))
        p4:add_equipment_upgrade(15, ((function() --[[ Line: 443 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v19 = v_u_1:new()
            v19.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 445 ]]
                return "PerfectPoints+";
            end;
            v19.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 446 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorBlue] = 1,
                    [v_u_2.Type.PerfectPoints] = 1
                } or {
                    [v_u_2.Type.PerfectPoints] = 1
                };
            end;
            v19.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 458 ]]
                return 5;
            end;
            v19.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 459 ]]
                return {
                    [3] = 1,
                    [2] = 1
                };
            end;
            v19.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 460 ]]
                return "rbxassetid://5682119773";
            end;
            return v19;
        end)()))
        p4:add_equipment_upgrade(16, ((function() --[[ Line: 464 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v20 = v_u_1:new()
            v20.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 466 ]]
                return "PerfectPoints++";
            end;
            v20.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 467 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorBlue] = 3,
                    [v_u_2.Type.PerfectPoints] = 2
                } or {
                    [v_u_2.Type.PerfectPoints] = 2,
                    [v_u_2.Type.FeverTime] = -1
                };
            end;
            v20.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 480 ]]
                return 10;
            end;
            v20.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 481 ]]
                return {
                    [4] = 1
                };
            end;
            v20.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 482 ]]
                return "rbxassetid://5682119827";
            end;
            return v20;
        end)()))
        p4:add_equipment_upgrade(17, ((function() --[[ Line: 486 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v21 = v_u_1:new()
            v21.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 488 ]]
                return "FeverMultiplier+";
            end;
            v21.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 489 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorRed] = 1,
                    [v_u_2.Type.FeverMultiplier] = 1
                } or {
                    [v_u_2.Type.FeverMultiplier] = 1
                };
            end;
            v21.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 501 ]]
                return 5;
            end;
            v21.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 502 ]]
                return {
                    [19] = 1,
                    [18] = 1
                };
            end;
            v21.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 503 ]]
                return "rbxassetid://5682120195";
            end;
            return v21;
        end)()))
        p4:add_equipment_upgrade(18, ((function() --[[ Line: 507 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v22 = v_u_1:new()
            v22.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 509 ]]
                return "FeverMultiplier++";
            end;
            v22.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 510 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorRed] = 3,
                    [v_u_2.Type.FeverMultiplier] = 3
                } or {
                    [v_u_2.Type.FeverMultiplier] = 3,
                    [v_u_2.Type.PerfectTime] = -1
                };
            end;
            v22.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 523 ]]
                return 10;
            end;
            v22.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 524 ]]
                return {
                    [20] = 1
                };
            end;
            v22.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 525 ]]
                return "rbxassetid://5682120138";
            end;
            return v22;
        end)()))
        p4:add_equipment_upgrade(19, ((function() --[[ Line: 529 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v23 = v_u_1:new()
            v23.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 531 ]]
                return "FeverTime+";
            end;
            v23.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 532 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorOrange] = 1,
                    [v_u_2.Type.FeverTime] = 1
                } or {
                    [v_u_2.Type.FeverTime] = 1
                };
            end;
            v23.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 544 ]]
                return 5;
            end;
            v23.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 545 ]]
                return {
                    [11] = 1,
                    [10] = 1
                };
            end;
            v23.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 546 ]]
                return "rbxassetid://5682120072";
            end;
            return v23;
        end)()))
        p4:add_equipment_upgrade(20, ((function() --[[ Line: 550 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v24 = v_u_1:new()
            v24.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 552 ]]
                return "FeverTime++";
            end;
            v24.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 553 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorOrange] = 3,
                    [v_u_2.Type.FeverTime] = 3
                } or {
                    [v_u_2.Type.FeverTime] = 3,
                    [v_u_2.Type.GreatTime] = -1,
                    [v_u_2.Type.OkayTime] = -2
                };
            end;
            v24.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 567 ]]
                return 10;
            end;
            v24.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 568 ]]
                return {
                    [12] = 1
                };
            end;
            v24.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 569 ]]
                return "rbxassetid://5682120011";
            end;
            return v24;
        end)()))
        p4:add_equipment_upgrade(21, ((function() --[[ Line: 573 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v25 = v_u_1:new()
            v25.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 575 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "Beat Points++" or "FeverDrainRate+";
            end;
            v25.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 582 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorOrange] = 6
                } or {
                    [v_u_2.Type.FeverDrainRate] = 3
                };
            end;
            v25.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 593 ]]
                return 10;
            end;
            v25.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 594 ]]
                return {
                    [12] = 1
                };
            end;
            v25.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 595 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310288" or "rbxassetid://2177381100";
            end;
            return v25;
        end)()))
        p4:add_equipment_upgrade(22, ((function() --[[ Line: 605 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (ref 3): v_u_2 ]]
            local v26 = v_u_1:new()
            v26.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 607 ]]
                return "Rush Points++";
            end;
            v26.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 608 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2 ]]
                return v_u_3.ColorGearStatsEnabled == true and {
                    [v_u_2.Type.ColorRed] = 6
                } or {};
            end;
            v26.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 618 ]]
                return 10;
            end;
            v26.get_craft_materials = function(_) --[[ Name: get_craft_materials ]] --[[ Line: 619 ]]
                return {
                    [20] = 1
                };
            end;
            v26.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 620 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3.ColorGearStatsEnabled == true and "rbxassetid://5587310404" or "rbxassetid://2177381100";
            end;
            return v26;
        end)()))
    end
};
