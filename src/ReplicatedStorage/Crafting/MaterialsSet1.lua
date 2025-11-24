-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:55 PM
-- Time elapsed: 24 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_3 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_4 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_5 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_9 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_10 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
return {
    ["add_to_craftdatabase"] = function(_, p_u_12) --[[ Name: add_to_craftdatabase ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_8, (copy 3): v_u_6, (copy 4): v_u_2, (copy 5): v_u_3, (copy 6): v_u_4, (copy 7): v_u_5, (copy 8): v_u_10, (copy 9): v_u_11, (copy 10): v_u_7, (copy 11): v_u_9 ]]
        p_u_12:add_to_material_dict(1, ((function() --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v13 = v_u_1:new()
            v13.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 19 ]]
                return "Small Blue Note";
            end;
            v13.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 20 ]]
                return "rbxassetid://9019090175";
            end;
            v13.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 21 ]]
                return "A small blue note used for crafting songs and gear upgrades.";
            end;
            v13.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 22 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T1;
            end;
            return v13;
        end)()))
        p_u_12:add_to_material_dict(2, ((function() --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v14 = v_u_1:new()
            v14.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 28 ]]
                return "Medium Blue Note";
            end;
            v14.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 29 ]]
                return "rbxassetid://9019090002";
            end;
            v14.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 30 ]]
                return "A medium blue note used for crafting songs and gear upgrades.";
            end;
            v14.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 31 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            return v14;
        end)()))
        p_u_12:add_to_material_dict(3, ((function() --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v15 = v_u_1:new()
            v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 37 ]]
                return "Large Blue Note";
            end;
            v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 38 ]]
                return "rbxassetid://9019089899";
            end;
            v15.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 39 ]]
                return "A large blue note used for crafting songs and gear upgrades.";
            end;
            v15.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            return v15;
        end)()))
        p_u_12:add_to_material_dict(4, ((function() --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v16 = v_u_1:new()
            v16.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 46 ]]
                return "Blue Gem";
            end;
            v16.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 47 ]]
                return "rbxassetid://9019089708";
            end;
            v16.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 48 ]]
                return "A blue gem used for crafting powerful gear upgrades.";
            end;
            v16.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 49 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            return v16;
        end)()))
        p_u_12:add_to_material_dict(5, ((function() --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v17 = v_u_1:new()
            v17.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 55 ]]
                return "Small Green Note";
            end;
            v17.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 56 ]]
                return "rbxassetid://9019089562";
            end;
            v17.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 57 ]]
                return "A small green note used for crafting songs and gear upgrades.";
            end;
            v17.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 58 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T1;
            end;
            return v17;
        end)()))
        p_u_12:add_to_material_dict(6, ((function() --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v18 = v_u_1:new()
            v18.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 64 ]]
                return "Medium Green Note";
            end;
            v18.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 65 ]]
                return "rbxassetid://9019089413";
            end;
            v18.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 66 ]]
                return "A medium green note used for crafting songs and gear upgrades.";
            end;
            v18.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 67 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            return v18;
        end)()))
        p_u_12:add_to_material_dict(7, ((function() --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v19 = v_u_1:new()
            v19.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 73 ]]
                return "Large Green Note";
            end;
            v19.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 74 ]]
                return "rbxassetid://9019089186";
            end;
            v19.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 75 ]]
                return "A large green note used for crafting songs and gear upgrades.";
            end;
            v19.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 76 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            return v19;
        end)()))
        p_u_12:add_to_material_dict(8, ((function() --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v20 = v_u_1:new()
            v20.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 82 ]]
                return "Green Gem";
            end;
            v20.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 83 ]]
                return "rbxassetid://9019089030";
            end;
            v20.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 84 ]]
                return "A green gem used for crafting powerful gear upgrades.";
            end;
            v20.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 85 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            return v20;
        end)()))
        p_u_12:add_to_material_dict(9, ((function() --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v21 = v_u_1:new()
            v21.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 91 ]]
                return "Small Orange Note";
            end;
            v21.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 92 ]]
                return "rbxassetid://9019088918";
            end;
            v21.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 93 ]]
                return "A small orange note used for crafting songs and gear upgrades.";
            end;
            v21.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 94 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T1;
            end;
            return v21;
        end)()))
        p_u_12:add_to_material_dict(10, ((function() --[[ Line: 98 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v22 = v_u_1:new()
            v22.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 100 ]]
                return "Medium Orange Note";
            end;
            v22.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 101 ]]
                return "rbxassetid://9019088788";
            end;
            v22.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 102 ]]
                return "A medium orange note used for crafting songs and gear upgrades.";
            end;
            v22.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 103 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            return v22;
        end)()))
        p_u_12:add_to_material_dict(11, ((function() --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v23 = v_u_1:new()
            v23.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 109 ]]
                return "Large Orange Note";
            end;
            v23.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 110 ]]
                return "rbxassetid://9019088612";
            end;
            v23.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 111 ]]
                return "A large orange note used for crafting songs and gear upgrades.";
            end;
            v23.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 112 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            return v23;
        end)()))
        p_u_12:add_to_material_dict(12, ((function() --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v24 = v_u_1:new()
            v24.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 118 ]]
                return "Orange Gem";
            end;
            v24.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 119 ]]
                return "rbxassetid://9019088413";
            end;
            v24.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 120 ]]
                return "An orange gem used for crafting powerful gear upgrades.";
            end;
            v24.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 121 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            return v24;
        end)()))
        p_u_12:add_to_material_dict(13, ((function() --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v25 = v_u_1:new()
            v25.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 127 ]]
                return "Small Purple Note";
            end;
            v25.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 128 ]]
                return "rbxassetid://9019088271";
            end;
            v25.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 129 ]]
                return "A small purple note used for crafting songs and gear upgrades.";
            end;
            v25.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 130 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T1;
            end;
            return v25;
        end)()))
        p_u_12:add_to_material_dict(14, ((function() --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v26 = v_u_1:new()
            v26.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 136 ]]
                return "Medium Purple Note";
            end;
            v26.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 137 ]]
                return "rbxassetid://9019088122";
            end;
            v26.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 138 ]]
                return "A medium purple note used for crafting songs and gear upgrades.";
            end;
            v26.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 139 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            return v26;
        end)()))
        p_u_12:add_to_material_dict(15, ((function() --[[ Line: 143 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v27 = v_u_1:new()
            v27.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 145 ]]
                return "Large Purple Note";
            end;
            v27.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 146 ]]
                return "rbxassetid://9019087959";
            end;
            v27.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 147 ]]
                return "A large purple note used for crafting songs and gear upgrades.";
            end;
            v27.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 148 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            return v27;
        end)()))
        p_u_12:add_to_material_dict(16, ((function() --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v28 = v_u_1:new()
            v28.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 154 ]]
                return "Purple Gem";
            end;
            v28.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 155 ]]
                return "rbxassetid://9019087831";
            end;
            v28.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 156 ]]
                return "A purple gem used for crafting powerful gear upgrades.";
            end;
            v28.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 157 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            return v28;
        end)()))
        p_u_12:add_to_material_dict(17, ((function() --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v29 = v_u_1:new()
            v29.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 163 ]]
                return "Small Red Note";
            end;
            v29.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 164 ]]
                return "rbxassetid://9019087630";
            end;
            v29.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 165 ]]
                return "A small red note used for crafting songs and gear upgrades.";
            end;
            v29.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 166 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T1;
            end;
            return v29;
        end)()))
        p_u_12:add_to_material_dict(18, ((function() --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v30 = v_u_1:new()
            v30.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 172 ]]
                return "Medium Red Note";
            end;
            v30.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 173 ]]
                return "rbxassetid://9019087450";
            end;
            v30.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 174 ]]
                return "A medium red note used for crafting songs and gear upgrades.";
            end;
            v30.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 175 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            return v30;
        end)()))
        p_u_12:add_to_material_dict(19, ((function() --[[ Line: 179 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v31 = v_u_1:new()
            v31.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 181 ]]
                return "Large Red Note";
            end;
            v31.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 182 ]]
                return "rbxassetid://9019087293";
            end;
            v31.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 183 ]]
                return "A large red note used for crafting songs and gear upgrades.";
            end;
            v31.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 184 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            return v31;
        end)()))
        p_u_12:add_to_material_dict(20, ((function() --[[ Line: 188 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v32 = v_u_1:new()
            v32.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 190 ]]
                return "Red Gem";
            end;
            v32.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 191 ]]
                return "rbxassetid://9019087068";
            end;
            v32.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 192 ]]
                return "A red gem used for crafting powerful gear upgrades.";
            end;
            v32.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 193 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            return v32;
        end)()))
        p_u_12:add_to_material_dict(21, ((function() --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v33 = v_u_1:new()
            v33.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 199 ]]
                return "Brass Token";
            end;
            v33.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 200 ]]
                return "rbxassetid://2625547255";
            end;
            v33.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 201 ]]
                return "A brass token used for crafting gear.";
            end;
            v33.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 202 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T5;
            end;
            return v33;
        end)()))
        p_u_12:add_to_material_dict(22, ((function() --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v34 = v_u_1:new()
            v34.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 208 ]]
                return "Silver Token";
            end;
            v34.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 209 ]]
                return "rbxassetid://2625547355";
            end;
            v34.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 210 ]]
                return "A silver token used for crafting gear.";
            end;
            v34.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 211 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T5;
            end;
            return v34;
        end)()))
        p_u_12:add_to_material_dict(23, ((function() --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v35 = v_u_1:new()
            v35.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 217 ]]
                return "Gold Token";
            end;
            v35.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 218 ]]
                return "rbxassetid://2625547437";
            end;
            v35.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 219 ]]
                return "A gold token used for crafting gear.";
            end;
            v35.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 220 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T5;
            end;
            return v35;
        end)()))
        local v_u_36 = v_u_8:new()
        local function f_add_fevericon_material(p37, p_u_38, p_u_39, p_u_40) --[[ Name: add_fevericon_material ]] --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_6, (copy 3): v_u_36, (ref 4): v_u_2, (copy 5): p_u_12 ]]
            if p_u_40 == nil then
                p_u_40 = v_u_1.Tier.T4
            end;
            v_u_6:is_enum_member(p_u_40, v_u_1.Tier)
            v_u_6:is_false(v_u_36:contains(p_u_38))
            v_u_36:add_set(p_u_38)
            local v_u_41 = v_u_2:singleton():get_fevericon_for_id(p_u_38)
            p_u_12:add_to_material_dict(p37, ((function() --[[ Line: 232 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_41, (copy 3): p_u_39, (ref 4): p_u_40, (copy 5): p_u_38 ]]
                local v42 = v_u_1:new()
                v42.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 234 ]]
                    --[[ Upvalues: (ref 1): v_u_41 ]]
                    return v_u_41:get_name() .. " Icon";
                end;
                v42.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 235 ]]
                    --[[ Upvalues: (ref 1): v_u_41 ]]
                    return v_u_41:get_icon();
                end;
                v42.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 236 ]]
                    --[[ Upvalues: (ref 1): p_u_39 ]]
                    local v43 = "An icon you can use to customize your displayed profile in chat and in-game. Customize it in the settings menu."
                    if p_u_39 == true then
                        v43 = v43 .. " (Not Tradeable)"
                    end;
                    return v43;
                end;
                v42.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 243 ]]
                    --[[ Upvalues: (ref 1): p_u_40 ]]
                    return p_u_40;
                end;
                v42.is_fever_icon = function(_) --[[ Name: is_fever_icon ]] --[[ Line: 244 ]]
                    return true;
                end;
                if p_u_39 == true then
                    v42.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 247 ]]
                        return false;
                    end;
                end;
                v42.get_fever_icon_id = function(_) --[[ Name: get_fever_icon_id ]] --[[ Line: 250 ]]
                    --[[ Upvalues: (ref 1): p_u_38 ]]
                    return p_u_38;
                end;
                return v42;
            end)()))
            v_u_41:set_material_id(p37)
        end;
        f_add_fevericon_material(24, 2)
        f_add_fevericon_material(25, 3)
        f_add_fevericon_material(26, 4)
        f_add_fevericon_material(27, 5)
        f_add_fevericon_material(28, 6)
        f_add_fevericon_material(29, 7)
        f_add_fevericon_material(30, 8)
        f_add_fevericon_material(31, 9)
        p_u_12:add_to_material_dict(32, ((function() --[[ Line: 268 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v44 = v_u_1:new()
            v44.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 270 ]]
                return "Upgrade Boost";
            end;
            v44.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 271 ]]
                return "rbxassetid://3553132593";
            end;
            v44.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 272 ]]
                return "Used to boost the success rate of upgrades above +5.";
            end;
            v44.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 273 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            return v44;
        end)()))
        p_u_12:add_to_material_dict(33, ((function() --[[ Line: 277 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v45 = v_u_1:new()
            v45.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 279 ]]
                return "Upgrade Protect";
            end;
            v45.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 280 ]]
                return "rbxassetid://3553132925";
            end;
            v45.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 281 ]]
                return "Used to protect upgrades from resetting when upgrading above +5.";
            end;
            v45.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 282 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            return v45;
        end)()))
        for v46 = 0, 22 do
            f_add_fevericon_material(v46 + 34, v46 + 11)
        end;
        local function f_add_gear_blueprint(p47, p48, p49, p50, p_u_51) --[[ Name: add_gear_blueprint ]] --[[ Line: 297 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (ref 3): v_u_1, (copy 4): p_u_12 ]]
            local v52 = v_u_3:color_to_name(p48)
            local v53 = v_u_4:slot_to_name(p49)
            local v54 = p50 and "Legendary " or ""
            local v_u_55 = string.format("%s%s %s Gear Blueprint", v54, v52, v53)
            local v_u_56 = string.format("A blueprint used to craft %s score enhancing %s%s gear.", v52, v54, v53)
            local l_T3_0 = v_u_1.Tier.T3
            if p50 then
                l_T3_0 = v_u_1.Tier.T4
            end;
            p_u_12:add_to_material_dict(p47, ((function() --[[ Line: 308 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_55, (copy 3): p_u_51, (copy 4): v_u_56, (ref 5): l_T3_0 ]]
                local v57 = v_u_1:new()
                v57.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 310 ]]
                    --[[ Upvalues: (ref 1): v_u_55 ]]
                    return v_u_55;
                end;
                v57.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 311 ]]
                    --[[ Upvalues: (ref 1): p_u_51 ]]
                    return p_u_51;
                end;
                v57.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 312 ]]
                    --[[ Upvalues: (ref 1): v_u_56 ]]
                    return v_u_56;
                end;
                v57.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 313 ]]
                    --[[ Upvalues: (ref 1): l_T3_0 ]]
                    return l_T3_0;
                end;
                v57.is_blueprint = function(_) --[[ Name: is_blueprint ]] --[[ Line: 315 ]]
                    return true;
                end;
                return v57;
            end)()))
        end;
        f_add_gear_blueprint(57, v_u_3.Blue, v_u_4.BACK, false, "rbxassetid://5573889255")
        f_add_gear_blueprint(58, v_u_3.Blue, v_u_4.FACE, false, "rbxassetid://5573889742")
        f_add_gear_blueprint(59, v_u_3.Blue, v_u_4.HAT, false, "rbxassetid://5573889644")
        f_add_gear_blueprint(60, v_u_3.Blue, v_u_4.NECK, false, "rbxassetid://5573889564")
        f_add_gear_blueprint(61, v_u_3.Blue, v_u_4.PANTS, false, "rbxassetid://5573889468")
        f_add_gear_blueprint(62, v_u_3.Blue, v_u_4.SHIRT, false, "rbxassetid://5573889356")
        f_add_gear_blueprint(63, v_u_3.Blue, v_u_4.BACK, true, "rbxassetid://5573887299")
        f_add_gear_blueprint(64, v_u_3.Blue, v_u_4.FACE, true, "rbxassetid://5573887460")
        f_add_gear_blueprint(65, v_u_3.Blue, v_u_4.HAT, true, "rbxassetid://5573887568")
        f_add_gear_blueprint(66, v_u_3.Blue, v_u_4.NECK, true, "rbxassetid://5573887669")
        f_add_gear_blueprint(67, v_u_3.Blue, v_u_4.PANTS, true, "rbxassetid://5573887764")
        f_add_gear_blueprint(68, v_u_3.Blue, v_u_4.SHIRT, true, "rbxassetid://5573887870")
        f_add_gear_blueprint(69, v_u_3.Green, v_u_4.BACK, false, "rbxassetid://5573891928")
        f_add_gear_blueprint(70, v_u_3.Green, v_u_4.FACE, false, "rbxassetid://5573892046")
        f_add_gear_blueprint(71, v_u_3.Green, v_u_4.HAT, false, "rbxassetid://5573892133")
        f_add_gear_blueprint(72, v_u_3.Green, v_u_4.NECK, false, "rbxassetid://5573892396")
        f_add_gear_blueprint(73, v_u_3.Green, v_u_4.PANTS, false, "rbxassetid://5573892288")
        f_add_gear_blueprint(74, v_u_3.Green, v_u_4.SHIRT, false, "rbxassetid://5573892211")
        f_add_gear_blueprint(75, v_u_3.Green, v_u_4.BACK, true, "rbxassetid://5573890416")
        f_add_gear_blueprint(76, v_u_3.Green, v_u_4.FACE, true, "rbxassetid://5573890510")
        f_add_gear_blueprint(77, v_u_3.Green, v_u_4.HAT, true, "rbxassetid://5573890875")
        f_add_gear_blueprint(78, v_u_3.Green, v_u_4.NECK, true, "rbxassetid://5573890781")
        f_add_gear_blueprint(79, v_u_3.Green, v_u_4.PANTS, true, "rbxassetid://5573890697")
        f_add_gear_blueprint(80, v_u_3.Green, v_u_4.SHIRT, true, "rbxassetid://5573890576")
        f_add_gear_blueprint(81, v_u_3.Orange, v_u_4.BACK, false, "rbxassetid://5573894265")
        f_add_gear_blueprint(82, v_u_3.Orange, v_u_4.FACE, false, "rbxassetid://5573894380")
        f_add_gear_blueprint(83, v_u_3.Orange, v_u_4.HAT, false, "rbxassetid://5573894481")
        f_add_gear_blueprint(84, v_u_3.Orange, v_u_4.NECK, false, "rbxassetid://5573894594")
        f_add_gear_blueprint(85, v_u_3.Orange, v_u_4.PANTS, false, "rbxassetid://5573894685")
        f_add_gear_blueprint(86, v_u_3.Orange, v_u_4.SHIRT, false, "rbxassetid://5573894792")
        f_add_gear_blueprint(87, v_u_3.Orange, v_u_4.BACK, true, "rbxassetid://5573893697")
        f_add_gear_blueprint(88, v_u_3.Orange, v_u_4.FACE, true, "rbxassetid://5573893800")
        f_add_gear_blueprint(89, v_u_3.Orange, v_u_4.HAT, true, "rbxassetid://5573893907")
        f_add_gear_blueprint(90, v_u_3.Orange, v_u_4.NECK, true, "rbxassetid://5573894003")
        f_add_gear_blueprint(91, v_u_3.Orange, v_u_4.PANTS, true, "rbxassetid://5573894186")
        f_add_gear_blueprint(92, v_u_3.Orange, v_u_4.SHIRT, true, "rbxassetid://5573894084")
        f_add_gear_blueprint(93, v_u_3.Purple, v_u_4.BACK, false, "rbxassetid://5573897344")
        f_add_gear_blueprint(94, v_u_3.Purple, v_u_4.FACE, false, "rbxassetid://5573897251")
        f_add_gear_blueprint(95, v_u_3.Purple, v_u_4.HAT, false, "rbxassetid://5573897118")
        f_add_gear_blueprint(96, v_u_3.Purple, v_u_4.NECK, false, "rbxassetid://5573897022")
        f_add_gear_blueprint(97, v_u_3.Purple, v_u_4.PANTS, false, "rbxassetid://5573896924")
        f_add_gear_blueprint(98, v_u_3.Purple, v_u_4.SHIRT, false, "rbxassetid://5573896824")
        f_add_gear_blueprint(99, v_u_3.Purple, v_u_4.BACK, true, "rbxassetid://5573896231")
        f_add_gear_blueprint(100, v_u_3.Purple, v_u_4.FACE, true, "rbxassetid://5573896328")
        f_add_gear_blueprint(101, v_u_3.Purple, v_u_4.HAT, true, "rbxassetid://5573896438")
        f_add_gear_blueprint(102, v_u_3.Purple, v_u_4.NECK, true, "rbxassetid://5573896538")
        f_add_gear_blueprint(103, v_u_3.Purple, v_u_4.PANTS, true, "rbxassetid://5573896608")
        f_add_gear_blueprint(104, v_u_3.Purple, v_u_4.SHIRT, true, "rbxassetid://5573896702")
        f_add_gear_blueprint(105, v_u_3.Red, v_u_4.BACK, false, "rbxassetid://5573898560")
        f_add_gear_blueprint(106, v_u_3.Red, v_u_4.FACE, false, "rbxassetid://5573898684")
        f_add_gear_blueprint(107, v_u_3.Red, v_u_4.HAT, false, "rbxassetid://5573898767")
        f_add_gear_blueprint(108, v_u_3.Red, v_u_4.NECK, false, "rbxassetid://5573898830")
        f_add_gear_blueprint(109, v_u_3.Red, v_u_4.PANTS, false, "rbxassetid://5573898933")
        f_add_gear_blueprint(110, v_u_3.Red, v_u_4.SHIRT, false, "rbxassetid://5573899038")
        f_add_gear_blueprint(111, v_u_3.Red, v_u_4.BACK, true, "rbxassetid://5573898036")
        f_add_gear_blueprint(112, v_u_3.Red, v_u_4.FACE, true, "rbxassetid://5573898157")
        f_add_gear_blueprint(113, v_u_3.Red, v_u_4.HAT, true, "rbxassetid://5573898249")
        f_add_gear_blueprint(114, v_u_3.Red, v_u_4.NECK, true, "rbxassetid://5573898323")
        f_add_gear_blueprint(115, v_u_3.Red, v_u_4.PANTS, true, "rbxassetid://5573898391")
        f_add_gear_blueprint(116, v_u_3.Red, v_u_4.SHIRT, true, "rbxassetid://5573898471")
        for v58 = 0, 30 do
            f_add_fevericon_material(v58 + 117, v58 + 34)
        end;
        p_u_12:add_to_material_dict(148, ((function() --[[ Line: 395 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v59 = v_u_1:new()
            v59.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 397 ]]
                return "Upgrade Cleaner";
            end;
            v59.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 398 ]]
                return "rbxassetid://8310412553";
            end;
            v59.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 399 ]]
                return "Used to clean upgrades from Gear.";
            end;
            v59.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 400 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            return v59;
        end)()))
        f_add_fevericon_material(149, 65)
        f_add_fevericon_material(150, 66)
        f_add_fevericon_material(151, 67)
        f_add_fevericon_material(152, 68)
        f_add_fevericon_material(153, 69)
        local v_u_60 = v_u_8:new()
        local function f_add_pet_material(p61, p_u_62) --[[ Name: add_pet_material ]] --[[ Line: 415 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (copy 3): v_u_60, (ref 4): v_u_10, (ref 5): v_u_3, (ref 6): v_u_11, (copy 7): p_u_12, (ref 8): v_u_1, (ref 9): v_u_7 ]]
            local v_u_63 = v_u_5:singleton():get_data_for_petid(p_u_62)
            v_u_6:is_non_nil(v_u_63)
            v_u_6:is_false(v_u_60:contains(p_u_62))
            v_u_60:add_set(p_u_62)
            local v_u_64 = string.format("%s Mini", v_u_63:get_name())
            local v65 = v_u_63:get_ranked_colors_list()
            local v66 = ""
            for v67 = 1, v65:count() do
                local v68 = v65:get(v67)
                if v_u_63:get_color_statmodifierobj()[v_u_10:elemental_color_to_gearstats_type(v68)] == nil then
                    break;
                end;
                if v67 ~= 1 then
                    if v67 ~= 2 then
                        break;
                    end;
                    v66 = v66 .. ", "
                end;
                v66 = v66 .. v_u_3:color_to_name(v68)
            end;
            local v_u_69
            if v_u_11.PetRankUpEnabled == true then
                v_u_69 = string.format("A sealed Mini you can add to your collection, or use to train and rank up other Minis. Elements: %s.", v66)
            else
                v_u_69 = string.format("A sealed Mini you can add to your collection, or use to train other Minis. Elements: %s.", v66)
            end;
            p_u_12:add_to_material_dict(p61, ((function() --[[ Line: 444 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_64, (copy 3): v_u_63, (ref 4): v_u_69, (ref 5): v_u_7, (copy 6): p_u_62 ]]
                local v70 = v_u_1:new()
                v70.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 446 ]]
                    --[[ Upvalues: (ref 1): v_u_64 ]]
                    return v_u_64;
                end;
                v70.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 447 ]]
                    --[[ Upvalues: (ref 1): v_u_63 ]]
                    return v_u_63:get_icon();
                end;
                v70.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 448 ]]
                    --[[ Upvalues: (ref 1): v_u_69 ]]
                    return v_u_69;
                end;
                v70.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 449 ]]
                    --[[ Upvalues: (ref 1): v_u_63, (ref 2): v_u_7, (ref 3): v_u_1 ]]
                    local v71 = v_u_63:get_rarity()
                    if v71 == v_u_7.Rarity.Tier1 then
                        return v_u_1.Tier.T2;
                    elseif v71 == v_u_7.Rarity.Tier2 or v71 == v_u_7.Rarity.Tier3 then
                        return v_u_1.Tier.T3;
                    elseif v71 == v_u_7.Rarity.Tier4 or v71 == v_u_7.Rarity.Tier4 then
                        return v_u_1.Tier.T4;
                    else
                        return v_u_1.Tier.T1;
                    end;
                end;
                v70.is_pet = function(_) --[[ Name: is_pet ]] --[[ Line: 461 ]]
                    return true;
                end;
                v70.get_pet_id = function(_) --[[ Name: get_pet_id ]] --[[ Line: 462 ]]
                    --[[ Upvalues: (ref 1): p_u_62 ]]
                    return p_u_62;
                end;
                return v70;
            end)()))
            v_u_63:set_material_id(p61)
        end;
        local v_u_72 = v_u_8:new()
        v_u_72:add_set(v_u_9:singleton():get_default_stage_id())
        v_u_72:add_set(v_u_9:singleton():get_default_dark_stage_id())
        local function f_add_stage_material(p73, p_u_74, p_u_75) --[[ Name: add_stage_material ]] --[[ Line: 472 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_6, (copy 3): v_u_72, (copy 4): p_u_12, (ref 5): v_u_1 ]]
            local v_u_76 = v_u_9:singleton():get_stage_info_for_id(p_u_74)
            v_u_6:is_non_nil(v_u_76)
            v_u_6:is_false(v_u_72:contains(p_u_74))
            v_u_72:add_set(p_u_74)
            p_u_12:add_to_material_dict(p73, ((function() --[[ Line: 478 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_76, (copy 3): p_u_75, (copy 4): p_u_74 ]]
                local v77 = v_u_1:new()
                v77.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 480 ]]
                    --[[ Upvalues: (ref 1): v_u_76 ]]
                    return string.format("%s Stage", v_u_76:get_name());
                end;
                v77.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 481 ]]
                    --[[ Upvalues: (ref 1): v_u_76 ]]
                    return v_u_76:get_icon();
                end;
                if p_u_75 == true then
                    v77.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 483 ]]
                        return "Allows you to select this stage to play on! (Not Tradeable)";
                    end;
                else
                    v77.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 485 ]]
                        return "Allows you to select this stage to play on!";
                    end;
                end;
                v77.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 487 ]]
                    --[[ Upvalues: (ref 1): v_u_1 ]]
                    return v_u_1.Tier.T3;
                end;
                if p_u_75 == true then
                    v77.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 490 ]]
                        return false;
                    end;
                end;
                v77.is_stage = function(_) --[[ Name: is_stage ]] --[[ Line: 493 ]]
                    return true;
                end;
                v77.get_stage_id = function(_) --[[ Name: get_stage_id ]] --[[ Line: 494 ]]
                    --[[ Upvalues: (ref 1): p_u_74 ]]
                    return p_u_74;
                end;
                return v77;
            end)()))
            v_u_76:set_material_id(p73)
        end;
        f_add_pet_material(154, 1)
        f_add_pet_material(155, 2)
        f_add_fevericon_material(156, 70)
        f_add_pet_material(157, 3)
        f_add_pet_material(158, 4)
        f_add_pet_material(159, 5)
        f_add_fevericon_material(160, 71)
        f_add_fevericon_material(161, 72)
        f_add_pet_material(162, 6)
        f_add_pet_material(163, 7)
        f_add_pet_material(164, 8)
        p_u_12:add_to_material_dict(165, ((function() --[[ Line: 513 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v78 = v_u_1:new()
            v78.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 515 ]]
                return "Small Note Box";
            end;
            v78.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 516 ]]
                return "rbxassetid://9021468542";
            end;
            v78.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 517 ]]
                return "Open this box to get 10 Small Notes of any color.";
            end;
            v78.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 518 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T1;
            end;
            v78.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 520 ]]
                return true;
            end;
            v78.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 521 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.SmallNote;
            end;
            return v78;
        end)()))
        p_u_12:add_to_material_dict(166, ((function() --[[ Line: 524 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v79 = v_u_1:new()
            v79.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 526 ]]
                return "Medium Note Box";
            end;
            v79.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 527 ]]
                return "rbxassetid://9021469017";
            end;
            v79.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 528 ]]
                return "Open this box to get 5 Medium Notes of any color.";
            end;
            v79.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 529 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            v79.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 531 ]]
                return true;
            end;
            v79.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 532 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.MediumNote;
            end;
            return v79;
        end)()))
        p_u_12:add_to_material_dict(167, ((function() --[[ Line: 535 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v80 = v_u_1:new()
            v80.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 537 ]]
                return "Large Note Box";
            end;
            v80.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 538 ]]
                return "rbxassetid://9021469134";
            end;
            v80.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 539 ]]
                return "Open this box to get 3 Large Notes of any color.";
            end;
            v80.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 540 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            v80.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 542 ]]
                return true;
            end;
            v80.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 543 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.LargeNote;
            end;
            return v80;
        end)()))
        p_u_12:add_to_material_dict(168, ((function() --[[ Line: 546 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v81 = v_u_1:new()
            v81.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 548 ]]
                return "Gem Box";
            end;
            v81.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 549 ]]
                return "rbxassetid://9021469292";
            end;
            v81.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 550 ]]
                return "Open this box to get 1 Gem of any color.";
            end;
            v81.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 551 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            v81.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 553 ]]
                return true;
            end;
            v81.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 554 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.Gem;
            end;
            return v81;
        end)()))
        p_u_12:add_to_material_dict(169, ((function() --[[ Line: 559 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v82 = v_u_1:new()
            v82.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 561 ]]
                return "Mini Box (1 Star)";
            end;
            v82.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 562 ]]
                return "rbxassetid://9470273636";
            end;
            v82.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 563 ]]
                return "Open this box to get a 1-Star Mini.";
            end;
            v82.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 564 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            v82.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 566 ]]
                return true;
            end;
            v82.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 567 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.MiniOneStar;
            end;
            return v82;
        end)()))
        f_add_fevericon_material(170, 73)
        f_add_pet_material(171, 9)
        f_add_pet_material(172, 10)
        f_add_fevericon_material(173, 74)
        f_add_fevericon_material(174, 75)
        f_add_pet_material(175, 11)
        f_add_pet_material(176, 12)
        f_add_pet_material(177, 13)
        f_add_fevericon_material(178, 76)
        f_add_fevericon_material(179, 77)
        f_add_fevericon_material(180, 78)
        f_add_fevericon_material(181, 79)
        f_add_fevericon_material(182, 80)
        f_add_fevericon_material(183, 81)
        f_add_fevericon_material(184, 82)
        f_add_fevericon_material(185, 83)
        f_add_pet_material(186, 14)
        f_add_pet_material(187, 15)
        f_add_fevericon_material(188, 84)
        f_add_stage_material(189, 3)
        f_add_fevericon_material(190, 85)
        f_add_pet_material(191, 16)
        f_add_fevericon_material(192, 86)
        f_add_pet_material(193, 17)
        f_add_fevericon_material(194, 87)
        p_u_12:add_to_material_dict(195, ((function() --[[ Line: 601 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v83 = v_u_1:new()
            v83.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 603 ]]
                return "Extended Cut Song Box (Normal)";
            end;
            v83.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 604 ]]
                return "rbxassetid://11111137048";
            end;
            v83.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 605 ]]
                return "Open this box to get an [EXTENDED CUT] Normal mode song.";
            end;
            v83.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            v83.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 608 ]]
                return true;
            end;
            v83.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 609 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.VIPSongNormal;
            end;
            return v83;
        end)()))
        p_u_12:add_to_material_dict(196, ((function() --[[ Line: 612 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v84 = v_u_1:new()
            v84.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 614 ]]
                return "Extended Cut Song Box (Hard)";
            end;
            v84.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 615 ]]
                return "rbxassetid://11111137159";
            end;
            v84.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 616 ]]
                return "Open this box to get an [EXTENDED CUT] Hard mode song.";
            end;
            v84.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 617 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            v84.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 619 ]]
                return true;
            end;
            v84.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 620 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.VIPSongHard;
            end;
            return v84;
        end)()))
        f_add_pet_material(197, 18)
        f_add_stage_material(198, 4)
        p_u_12:add_to_material_dict(199, ((function() --[[ Line: 627 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v85 = v_u_1:new()
            v85.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 629 ]]
                return "Mini Box (2 Star)";
            end;
            v85.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 630 ]]
                return "rbxassetid://9470273754";
            end;
            v85.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 631 ]]
                return "Open this box to get a 2-Star Mini.";
            end;
            v85.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 632 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            v85.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 634 ]]
                return true;
            end;
            v85.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 635 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.MiniTwoStar;
            end;
            return v85;
        end)()))
        f_add_fevericon_material(200, 88)
        f_add_pet_material(201, 19)
        f_add_fevericon_material(202, 89)
        f_add_stage_material(203, 5)
        f_add_fevericon_material(204, 90)
        f_add_fevericon_material(205, 91)
        f_add_pet_material(206, 20)
        f_add_stage_material(207, 6)
        f_add_pet_material(208, 21)
        f_add_fevericon_material(209, 92)
        f_add_fevericon_material(210, 93)
        f_add_stage_material(211, 9)
        f_add_pet_material(212, 22)
        f_add_fevericon_material(213, 94)
        f_add_fevericon_material(214, 95)
        f_add_fevericon_material(215, 96)
        f_add_pet_material(216, 23)
        f_add_pet_material(217, 24)
        f_add_pet_material(218, 25)
        f_add_stage_material(219, 8)
        f_add_fevericon_material(220, 97)
        f_add_pet_material(221, 26)
        f_add_fevericon_material(222, 98)
        f_add_fevericon_material(223, 99)
        f_add_stage_material(224, 7)
        f_add_pet_material(225, 27)
        f_add_pet_material(226, 28)
        f_add_fevericon_material(227, 100)
        f_add_fevericon_material(228, 101)
        f_add_fevericon_material(229, 102)
        f_add_fevericon_material(230, 103)
        f_add_fevericon_material(231, 104)
        f_add_fevericon_material(232, 105)
        f_add_fevericon_material(233, 106)
        f_add_fevericon_material(234, 107)
        f_add_fevericon_material(235, 108)
        f_add_fevericon_material(236, 109)
        f_add_fevericon_material(237, 110)
        f_add_fevericon_material(238, 111)
        f_add_pet_material(239, 29)
        f_add_stage_material(240, 10)
        f_add_pet_material(241, 30)
        f_add_pet_material(242, 31)
        f_add_fevericon_material(243, 112)
        f_add_fevericon_material(244, 113)
        f_add_fevericon_material(245, 114)
        f_add_fevericon_material(246, 115)
        f_add_pet_material(247, 32)
        f_add_pet_material(248, 33)
        p_u_12:add_to_material_dict(249, ((function() --[[ Line: 691 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v86 = v_u_1:new()
            v86.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 693 ]]
                return "Token Box";
            end;
            v86.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 694 ]]
                return "rbxassetid://10504912917";
            end;
            v86.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 695 ]]
                return "Open this box to get a token of your choice.";
            end;
            v86.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 696 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            v86.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 698 ]]
                return true;
            end;
            v86.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 699 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.Token;
            end;
            return v86;
        end)()))
        p_u_12:add_to_material_dict(250, ((function() --[[ Line: 702 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v87 = v_u_1:new()
            v87.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 704 ]]
                return "Leaderboard Ticket";
            end;
            v87.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 705 ]]
                return "rbxassetid://10530097746";
            end;
            v87.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 706 ]]
                return "A ticket earned from competing in weekly and team leaderboards. Can be exchanged for hard-to-find rewards! (Not Tradeable)";
            end;
            v87.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 707 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            v87.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 708 ]]
                return false;
            end;
            v87.is_leaderboard_ticket = function(_) --[[ Name: is_leaderboard_ticket ]] --[[ Line: 709 ]]
                return true;
            end;
            return v87;
        end)()))
        f_add_fevericon_material(251, 116)
        f_add_pet_material(252, 34)
        f_add_fevericon_material(253, 117)
        f_add_stage_material(254, 11)
        f_add_stage_material(255, 12)
        f_add_stage_material(256, 13)
        f_add_pet_material(257, 35)
        f_add_fevericon_material(258, 118)
        f_add_fevericon_material(259, 119)
        f_add_pet_material(260, 36)
        f_add_fevericon_material(261, 120)
        f_add_pet_material(262, 37)
        f_add_fevericon_material(263, 121)
        f_add_pet_material(264, 38)
        f_add_fevericon_material(265, 122)
        f_add_pet_material(266, 39)
        f_add_pet_material(267, 40)
        f_add_fevericon_material(268, 123)
        f_add_pet_material(269, 41)
        f_add_fevericon_material(270, 124)
        p_u_12:add_to_material_dict(271, ((function() --[[ Line: 738 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v88 = v_u_1:new()
            v88.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 740 ]]
                return "Extended Cut Song Box (Normal)";
            end;
            v88.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 741 ]]
                return "rbxassetid://11111137048";
            end;
            v88.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 742 ]]
                return "Open this box to get an [EXTENDED CUT] Normal mode song. (Not Tradeable)";
            end;
            v88.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 743 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            v88.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 745 ]]
                return true;
            end;
            v88.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 746 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.VIPSongNormal;
            end;
            v88.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 747 ]]
                return false;
            end;
            return v88;
        end)()))
        p_u_12:add_to_material_dict(272, ((function() --[[ Line: 750 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v89 = v_u_1:new()
            v89.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 752 ]]
                return "Extended Cut Song Box (Hard)";
            end;
            v89.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 753 ]]
                return "rbxassetid://11111137159";
            end;
            v89.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 754 ]]
                return "Open this box to get an [EXTENDED CUT] Hard mode song. (Not Tradeable)";
            end;
            v89.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 755 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            v89.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 757 ]]
                return true;
            end;
            v89.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 758 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.VIPSongHard;
            end;
            v89.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 759 ]]
                return false;
            end;
            return v89;
        end)()))
        f_add_fevericon_material(273, 125)
        f_add_pet_material(274, 42)
        f_add_pet_material(275, 43)
        f_add_fevericon_material(276, 126)
        f_add_pet_material(277, 44)
        f_add_fevericon_material(278, 127)
        f_add_pet_material(279, 45)
        f_add_fevericon_material(280, 128)
        f_add_pet_material(281, 46)
        f_add_fevericon_material(282, 129)
        f_add_pet_material(283, 47)
        f_add_fevericon_material(284, 130)
        f_add_fevericon_material(285, 131)
        f_add_pet_material(286, 48)
        f_add_stage_material(287, 14)
        f_add_stage_material(288, 15)
        f_add_pet_material(289, 49)
        f_add_fevericon_material(290, 132)
        f_add_fevericon_material(291, 133)
        p_u_12:add_to_material_dict(292, ((function() --[[ Line: 783 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v90 = v_u_1:new()
            v90.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 785 ]]
                return "Mini Box (1 Star)";
            end;
            v90.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 786 ]]
                return "rbxassetid://9470273636";
            end;
            v90.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 787 ]]
                return "Open this box to get a 1-Star Mini. (Not Tradeable)";
            end;
            v90.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 788 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            v90.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 790 ]]
                return true;
            end;
            v90.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 791 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.MiniOneStar;
            end;
            v90.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 792 ]]
                return false;
            end;
            return v90;
        end)()))
        p_u_12:add_to_material_dict(293, ((function() --[[ Line: 795 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v91 = v_u_1:new()
            v91.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 797 ]]
                return "Mini Box (2 Star)";
            end;
            v91.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 798 ]]
                return "rbxassetid://9470273754";
            end;
            v91.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 799 ]]
                return "Open this box to get a 2-Star Mini. (Not Tradeable)";
            end;
            v91.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 800 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T4;
            end;
            v91.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 802 ]]
                return true;
            end;
            v91.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 803 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.MiniTwoStar;
            end;
            v91.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 804 ]]
                return false;
            end;
            return v91;
        end)()))
        p_u_12:add_to_material_dict(294, ((function() --[[ Line: 807 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v92 = v_u_1:new()
            v92.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 809 ]]
                return "Upgrade Boost";
            end;
            v92.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 810 ]]
                return "rbxassetid://3553132593";
            end;
            v92.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 811 ]]
                return "Used to boost the success rate of upgrades above +5. These will be used first when upgrading. (Not Tradeable)";
            end;
            v92.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 812 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            v92.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 813 ]]
                return false;
            end;
            return v92;
        end)()))
        p_u_12:add_to_material_dict(295, ((function() --[[ Line: 817 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v93 = v_u_1:new()
            v93.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 819 ]]
                return "Upgrade Protect";
            end;
            v93.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 820 ]]
                return "rbxassetid://3553132925";
            end;
            v93.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 821 ]]
                return "Used to protect upgrades from resetting when upgrading above +5. These will be used first when upgrading. (Not Tradeable)";
            end;
            v93.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 822 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T3;
            end;
            v93.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 823 ]]
                return false;
            end;
            return v93;
        end)()))
        f_add_pet_material(296, 50)
        f_add_stage_material(297, 16)
        f_add_fevericon_material(298, 134)
        f_add_fevericon_material(299, 135)
        f_add_fevericon_material(300, 136)
        f_add_fevericon_material(301, 137)
        f_add_fevericon_material(302, 139)
        f_add_fevericon_material(303, 140)
        f_add_fevericon_material(304, 141)
        f_add_fevericon_material(305, 142)
        f_add_fevericon_material(306, 143)
        f_add_fevericon_material(307, 144)
        f_add_pet_material(308, 51)
        f_add_fevericon_material(309, 145)
        f_add_fevericon_material(310, 146)
        f_add_fevericon_material(311, 147)
        f_add_fevericon_material(312, 148)
        f_add_pet_material(313, 52)
        f_add_fevericon_material(314, 149)
        f_add_fevericon_material(315, 150)
        f_add_fevericon_material(316, 151)
        f_add_pet_material(317, 53)
        f_add_fevericon_material(318, 152)
        f_add_stage_material(319, 17)
        f_add_stage_material(320, 18)
        f_add_pet_material(321, 54)
        f_add_fevericon_material(322, 153)
        f_add_fevericon_material(323, 154)
        f_add_pet_material(324, 55)
        f_add_fevericon_material(325, 155)
        f_add_fevericon_material(326, 156)
        f_add_pet_material(327, 56)
        f_add_pet_material(328, 57)
        f_add_stage_material(329, 19)
        f_add_pet_material(330, 58)
        f_add_fevericon_material(331, 157)
        f_add_fevericon_material(332, 158)
        f_add_fevericon_material(333, 159)
        f_add_pet_material(334, 59)
        f_add_fevericon_material(335, 160)
        f_add_fevericon_material(336, 161)
        f_add_pet_material(337, 60)
        f_add_stage_material(338, 20)
        f_add_fevericon_material(339, 162)
        f_add_pet_material(340, 61)
        f_add_fevericon_material(341, 163)
        f_add_fevericon_material(342, 164)
        f_add_fevericon_material(343, 165)
        f_add_pet_material(344, 62)
        f_add_fevericon_material(345, 166)
        f_add_stage_material(346, 21)
        f_add_stage_material(347, 22)
        f_add_pet_material(348, 63)
        f_add_fevericon_material(349, 167)
        f_add_fevericon_material(350, 168, true, v_u_1.Tier.T1)
        f_add_fevericon_material(351, 169, true, v_u_1.Tier.T1)
        f_add_fevericon_material(352, 170, true, v_u_1.Tier.T1)
        f_add_fevericon_material(353, 171)
        f_add_pet_material(354, 64)
        f_add_fevericon_material(355, 172, true)
        f_add_fevericon_material(356, 173)
        f_add_fevericon_material(357, 174)
        f_add_fevericon_material(358, 175)
        f_add_fevericon_material(359, 176)
        f_add_pet_material(360, 65)
        f_add_pet_material(361, 66)
        f_add_fevericon_material(362, 177)
        f_add_fevericon_material(363, 178)
        f_add_fevericon_material(364, 179)
        f_add_fevericon_material(365, 180)
        f_add_fevericon_material(366, 181, true)
        p_u_12:add_to_material_dict(367, ((function() --[[ Line: 904 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v94 = v_u_1:new()
            v94.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 906 ]]
                return "Dance Box";
            end;
            v94.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 907 ]]
                return "rbxassetid://16318422388";
            end;
            v94.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 908 ]]
                return "Open this box to get a rare dance that you do not currently own.";
            end;
            v94.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 909 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            v94.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 911 ]]
                return true;
            end;
            v94.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 912 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.Dance;
            end;
            v94.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 913 ]]
                return true;
            end;
            return v94;
        end)()))
        p_u_12:add_to_material_dict(368, ((function() --[[ Line: 916 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            local v95 = v_u_1:new()
            v95.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 918 ]]
                return "Dance Box";
            end;
            v95.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 919 ]]
                return "rbxassetid://16318422388";
            end;
            v95.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 920 ]]
                return "Open this box to get a rare dance that you do not currently own. (Not Tradeable)";
            end;
            v95.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 921 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.Tier.T2;
            end;
            v95.is_box = function(_) --[[ Name: is_box ]] --[[ Line: 923 ]]
                return true;
            end;
            v95.get_box_type = function(_) --[[ Name: get_box_type ]] --[[ Line: 924 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1.BoxType.Dance;
            end;
            v95.is_tradeable = function(_) --[[ Name: is_tradeable ]] --[[ Line: 925 ]]
                return false;
            end;
            return v95;
        end)()))
        f_add_fevericon_material(369, 182)
        f_add_pet_material(370, 67)
        f_add_stage_material(371, 23)
        f_add_stage_material(372, 24)
        f_add_fevericon_material(373, 183)
        f_add_fevericon_material(374, 184)
        f_add_fevericon_material(375, 185)
        f_add_fevericon_material(376, 186)
        f_add_fevericon_material(377, 187)
        f_add_fevericon_material(378, 188)
        f_add_fevericon_material(379, 189)
        f_add_fevericon_material(380, 190)
        f_add_fevericon_material(381, 191)
        f_add_fevericon_material(382, 192)
        f_add_pet_material(383, 68)
        f_add_pet_material(384, 69)
        f_add_fevericon_material(385, 193)
        f_add_fevericon_material(386, 194)
        f_add_pet_material(387, 70)
        f_add_fevericon_material(388, 195)
        f_add_fevericon_material(389, 196)
        f_add_pet_material(390, 71)
        f_add_stage_material(391, 25)
        f_add_stage_material(392, 26)
        f_add_fevericon_material(393, 197)
        f_add_fevericon_material(394, 198)
        f_add_fevericon_material(395, 199)
        f_add_pet_material(396, 72)
        f_add_fevericon_material(397, 200)
        f_add_stage_material(398, 27)
        f_add_pet_material(399, 73)
        f_add_fevericon_material(400, 201)
        f_add_fevericon_material(401, 202)
        f_add_fevericon_material(402, 203)
        f_add_fevericon_material(403, 204)
        f_add_fevericon_material(404, 205)
        f_add_fevericon_material(405, 206)
        f_add_fevericon_material(406, 207)
        f_add_fevericon_material(407, 208)
        f_add_fevericon_material(408, 209)
        f_add_fevericon_material(409, 210)
        f_add_pet_material(410, 74)
        f_add_fevericon_material(411, 211)
        f_add_fevericon_material(412, 212)
        f_add_fevericon_material(413, 213, true)
        f_add_fevericon_material(414, 214)
        f_add_fevericon_material(415, 215)
        f_add_stage_material(416, 28)
        f_add_fevericon_material(417, 216)
        f_add_pet_material(418, 75)
        f_add_fevericon_material(419, 217)
        f_add_pet_material(420, 76)
        f_add_fevericon_material(421, 218)
        f_add_fevericon_material(422, 219)
        f_add_fevericon_material(423, 220)
        f_add_pet_material(424, 77)
        f_add_fevericon_material(425, 221)
        f_add_pet_material(426, 78)
        f_add_fevericon_material(427, 222)
        f_add_fevericon_material(428, 223)
        f_add_pet_material(429, 79)
        f_add_fevericon_material(430, 224)
        f_add_stage_material(431, 29)
        f_add_fevericon_material(432, 225)
        f_add_fevericon_material(433, 226)
        f_add_pet_material(434, 80)
        f_add_fevericon_material(435, 227)
        f_add_pet_material(436, 81)
        f_add_fevericon_material(437, 228)
        f_add_fevericon_material(438, 229)
        f_add_fevericon_material(439, 230)
        f_add_fevericon_material(440, 231)
        f_add_fevericon_material(441, 232)
        f_add_fevericon_material(442, 233)
        f_add_fevericon_material(443, 234)
        f_add_fevericon_material(444, 235)
        f_add_fevericon_material(445, 236)
        f_add_fevericon_material(446, 237)
        f_add_fevericon_material(447, 238)
        f_add_fevericon_material(448, 239)
        f_add_fevericon_material(449, 240)
        f_add_fevericon_material(450, 241, true)
        f_add_fevericon_material(451, 242)
        f_add_pet_material(452, 82)
        f_add_fevericon_material(453, 243)
        f_add_fevericon_material(454, 244)
        f_add_pet_material(455, 83)
        f_add_fevericon_material(456, 245)
        f_add_fevericon_material(457, 246)
        f_add_fevericon_material(458, 247)
        f_add_pet_material(459, 84)
        f_add_fevericon_material(460, 248)
    end
};
