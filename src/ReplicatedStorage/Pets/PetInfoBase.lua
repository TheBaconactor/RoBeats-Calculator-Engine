-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_7 = {
    ["Rarity"] = {
        ["Tier1"] = 1,
        ["Tier2"] = 2,
        ["Tier3"] = 3,
        ["Tier4"] = 4,
        ["Tier5"] = 5
    }
}
v_u_7.new = function(_) --[[ Name: new ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_3 ]]
    local v9 = {
        ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 22 ]]
            return "";
        end,
        ["get_description"] = function(_) --[[ Name: get_description ]] --[[ Line: 23 ]]
            return "";
        end,
        ["create_character"] = function(_, _, _, p8) --[[ Name: create_character ]] --[[ Line: 24 ]]
            return p8(nil);
        end,
        ["get_base_statmodifierobj"] = function(_) --[[ Name: get_base_statmodifierobj ]] --[[ Line: 25 ]]
            return {};
        end,
        ["get_color_statmodifierobj"] = function(_) --[[ Name: get_color_statmodifierobj ]] --[[ Line: 26 ]]
            return {};
        end,
        ["get_icon"] = function(_) --[[ Name: get_icon ]] --[[ Line: 27 ]]
            return "";
        end
    }
    v9.get_rarity = function(_) --[[ Name: get_rarity ]] --[[ Line: 28 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        return v_u_7.Rarity.Tier1;
    end;
    local v_u_10 = v_u_4:invalid_material_id()
    v9.set_material_id = function(_, p11) --[[ Name: set_material_id ]] --[[ Line: 31 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        v_u_10 = p11
    end;
    v9.get_material_id = function(_) --[[ Name: get_material_id ]] --[[ Line: 32 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        return v_u_10;
    end;
    v9.get_ranked_colors_list = function(p12) --[[ Name: get_ranked_colors_list ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        local v13 = v_u_2:statsdict_base()
        v_u_2:statsdict_apply_statmodifierobj(v13, p12:get_color_statmodifierobj())
        return v_u_2:statsdict_get_ranked_colors(v13), v13;
    end;
    v9.get_active_ranked_colors_list = function(p14) --[[ Name: get_active_ranked_colors_list ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        local v15, v_u_16 = p14:get_ranked_colors_list()
        v15:remove_if(function(p17) --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_2 ]]
            return v_u_16[v_u_2:elemental_color_to_gearstats_type(p17)] == 0;
        end)
        return v15;
    end;
    v9.get_colors_set = function(p18) --[[ Name: get_colors_set ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3 ]]
        local v19 = p18:get_ranked_colors_list()
        v_u_2:ranked_colors_statsdict_filter(v19, p18:get_color_statmodifierobj())
        return v_u_3:new():add_set_from_table_list(v19:get_table());
    end;
    return v9;
end;
local v_u_20 = Vector3.new(0.6, 0.6, 0.3)
v_u_7.do_environment_setup = function(_) --[[ Name: do_environment_setup ]] --[[ Line: 62 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_6, (ref 3): v_u_20 ]]
    v_u_20 = v_u_5:singleton():get_category_default(v_u_6.Category.PetNPC).PrimaryPart.Size
end;
v_u_7.get_default_pet_root_part_size = function(_) --[[ Name: get_default_pet_root_part_size ]] --[[ Line: 67 ]]
    --[[ Upvalues: (ref 1): v_u_20 ]]
    return v_u_20;
end;
v_u_7.spawn_pet_npc_from_name = function(_, p21, p_u_22, p_u_23, p_u_24) --[[ Name: spawn_pet_npc_from_name ]] --[[ Line: 69 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_5, (ref 4): v_u_20 ]]
    local v25 = v_u_6:get_category_name_to_id(v_u_6.Category.PetNPC):get(p21)
    if v25 == nil then
        v_u_1:warnf("PetInfoBase:spawn_pet_npc_from_name(%s) modelid not found (nil)", (tostring(p21)))
    end;
    v_u_5:singleton():load_model_category(v25, v_u_6.Category.PetNPC, function(p_u_26) --[[ Line: 74 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_20, (copy 3): p_u_23, (copy 4): p_u_24 ]]
        p_u_26.Parent = p_u_22
        p_u_26.PrimaryPart.Size = v_u_20
        if p_u_23 and p_u_23.FnPostCreate then
            p_u_23.FnPostCreate(p_u_26)
        end;
        if p_u_23 and p_u_23.WaitBeforeFinish == true then
            spawn(function() --[[ Line: 81 ]]
                --[[ Upvalues: (ref 1): p_u_24, (copy 2): p_u_26 ]]
                p_u_24(p_u_26, p_u_26)
            end)
        else
            p_u_24(p_u_26, p_u_26)
        end;
    end)
end;
return v_u_7;
