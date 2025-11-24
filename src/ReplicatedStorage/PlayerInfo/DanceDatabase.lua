-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:06 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabaseData)
local v_u_8 = {
    ["DanceInfoBase"] = {}
}
v_u_8.DanceInfoBase.new = function(_) --[[ Name: new ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_6 ]]
    local v9 = {
        ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 19 ]]
            return "";
        end,
        ["get_description"] = function(_) --[[ Name: get_description ]] --[[ Line: 20 ]]
            return "";
        end,
        ["get_icon"] = function(_) --[[ Name: get_icon ]] --[[ Line: 21 ]]
            return "";
        end,
        ["get_assetid"] = function(_) --[[ Name: get_assetid ]] --[[ Line: 22 ]]
            return "";
        end,
        ["is_dance_default_owned"] = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 23 ]]
            return false;
        end
    }
    local v_u_10 = -1
    v9.set_dance_id = function(_, p11) --[[ Name: set_dance_id ]] --[[ Line: 16 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        v_u_10 = p11
    end;
    v9.get_dance_id = function(_) --[[ Name: get_dance_id ]] --[[ Line: 17 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        return v_u_10;
    end;
    v9.get_dance_type = function(p12) --[[ Name: get_dance_type ]] --[[ Line: 24 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_4 ]]
        local v13 = p12:internal_get_dance_type()
        v_u_5:is_enum_member(v13, v_u_4)
        return v13;
    end;
    v9.internal_get_dance_type = function(p14) --[[ Name: internal_get_dance_type ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        v_u_2:errf("DanceInfoBase:internal_get_dance_type must override(%s)", (tostring(p14:get_dance_id())))
    end;
    v9.get_dance_rarity = function(_) --[[ Name: get_dance_rarity ]] --[[ Line: 32 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        return v_u_6.Default;
    end;
    return v9;
end;
v_u_8.new = function(_) --[[ Name: new ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_7, (copy 3): v_u_8, (copy 4): v_u_5, (copy 5): v_u_6, (copy 6): v_u_4, (copy 7): v_u_3, (copy 8): v_u_2 ]]
    local v_u_15 = {}
    local v_u_16 = v_u_1:new()
    local v_u_17 = v_u_1:new()
    local v_u_18 = v_u_1:new()
    local v_u_19 = v_u_1:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 44 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_15, (ref 3): v_u_8, (copy 4): v_u_16, (ref 5): v_u_5, (ref 6): v_u_6, (ref 7): v_u_4, (copy 8): v_u_19, (ref 9): v_u_3 ]]
        v_u_7:add_dance_data(v_u_15, v_u_8)
        for v20 = 1, v_u_16:count() do
            local v21 = v_u_16:get(v20)
            v_u_5:is_non_nil(v21)
            v_u_5:is_enum_member(v21:get_dance_rarity(), v_u_6)
            v_u_5:is_enum_member(v21:get_dance_type(), v_u_4)
            if v21:is_dance_default_owned() then
                v_u_19:add_set(v20)
            end;
        end;
        if v_u_3.AllDancesDefaultOwned == true then
            for v22 = 1, v_u_16:count() do
                v_u_16:get(v22).is_dance_default_owned = function(_) --[[ Name: is_dance_default_owned ]] --[[ Line: 64 ]]
                    return true;
                end
            end;
        end;
    end;
    v_u_15.key_itr = function(_) --[[ Name: key_itr ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:key_itr();
    end;
    v_u_15.add_dance_for_id = function(_, p23, p24) --[[ Name: add_dance_for_id ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_2, (copy 3): v_u_18 ]]
        if v_u_16:contains(p23) then
            v_u_2:errf("DanceDatabase:add_dance_for_id contains id(%s)", (tostring(p23)))
        end;
        p24:set_dance_id(p23)
        v_u_16:add(p23, p24)
        v_u_18:add(p24:get_assetid(), p23)
    end;
    v_u_15.assetid_is_dance = function(_, p25) --[[ Name: assetid_is_dance ]] --[[ Line: 81 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        return v_u_18:contains(p25);
    end;
    v_u_15.assetid_to_danceid = function(_, p26) --[[ Name: assetid_to_danceid ]] --[[ Line: 82 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        return v_u_18:get(p26);
    end;
    v_u_15.contains_dance_for_id = function(_, p27) --[[ Name: contains_dance_for_id ]] --[[ Line: 84 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:contains(p27);
    end;
    v_u_15.get_dance_info_for_id = function(_, p28) --[[ Name: get_dance_info_for_id ]] --[[ Line: 86 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:get(p28);
    end;
    v_u_15.is_dance_default_owned = function(_, p29) --[[ Name: is_dance_default_owned ]] --[[ Line: 87 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:get(p29):is_dance_default_owned();
    end;
    v_u_15.get_dance_name_for_id = function(_, p30) --[[ Name: get_dance_name_for_id ]] --[[ Line: 88 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:get(p30):get_name();
    end;
    v_u_15.get_dance_description_for_id = function(_, p31) --[[ Name: get_dance_description_for_id ]] --[[ Line: 89 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:get(p31):get_description();
    end;
    v_u_15.get_dance_icon_for_id = function(_, p32) --[[ Name: get_dance_icon_for_id ]] --[[ Line: 90 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:get(p32):get_icon();
    end;
    v_u_15.get_dance_type_for_id = function(_, p33) --[[ Name: get_dance_type_for_id ]] --[[ Line: 91 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:get(p33):get_dance_type();
    end;
    v_u_15.get_dance_rarity_for_id = function(_, p34) --[[ Name: get_dance_rarity_for_id ]] --[[ Line: 92 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:get(p34):get_dance_rarity();
    end;
    v_u_15.get_dance_assetid_for_id = function(_, p35) --[[ Name: get_dance_assetid_for_id ]] --[[ Line: 93 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:get(p35):get_assetid();
    end;
    v_u_15.count = function(_) --[[ Name: count ]] --[[ Line: 94 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16:count();
    end;
    v_u_15.get_default_owned_danceid_set = function(_) --[[ Name: get_default_owned_danceid_set ]] --[[ Line: 95 ]]
        --[[ Upvalues: (copy 1): v_u_19 ]]
        return v_u_19;
    end;
    v_u_15.get_dance_animation_for_id = function(_, p36) --[[ Name: get_dance_animation_for_id ]] --[[ Line: 97 ]]
        --[[ Upvalues: (copy 1): v_u_17, (copy 2): v_u_16, (ref 3): v_u_2 ]]
        if v_u_17:contains(p36) ~= true then
            if v_u_16:contains(p36) ~= true then
                v_u_2:errf("DanceDatabase:get_dance_animation_for_id does not contain id(%s)", (tostring(p36)))
            end;
            local v37 = v_u_16:get(p36)
            local l_Animation_0 = Instance.new("Animation")
            l_Animation_0.AnimationId = v37:get_assetid()
            v_u_17:add(p36, l_Animation_0)
        end;
        return v_u_17:get(p36);
    end;
    v_u_15.get_dancedatabase_info = function(_) --[[ Name: get_dancedatabase_info ]] --[[ Line: 110 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        local v38 = {}
        for v39, v40 in v_u_16:key_itr() do
            v38[#v38 + 1] = {
                ["dance_id"] = v39,
                ["name"] = v40:get_name(),
                ["default"] = v40:is_dance_default_owned(),
                ["rarity"] = v40:get_dance_rarity()
            }
        end;
        return v38;
    end;
    v_u_15.print_debug_dance_data = function(_) --[[ Name: print_debug_dance_data ]] --[[ Line: 123 ]]
        --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_6, (ref 3): v_u_2 ]]
        local v41 = ""
        for v42, v43 in v_u_16:key_itr() do
            local v44
            if v43:get_dance_rarity() == v_u_6.Default then
                v44 = v41 .. "_"
            elseif v43:get_dance_rarity() == v_u_6.Common then
                v44 = v41 .. "*"
            elseif v43:get_dance_rarity() == v_u_6.Rare then
                v44 = v41 .. "**"
            else
                v44 = v41 .. "****"
            end;
            v41 = v44 .. string.format("Dance(%d) Name(%s)\n", v42, v43:get_name())
        end;
        v_u_2:warnf(v41)
    end;
    f_cons()
    return v_u_15;
end;
local v_u_45 = v_u_8:new()
v_u_8.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 145 ]]
    --[[ Upvalues: (copy 1): v_u_45 ]]
    return v_u_45;
end;
return v_u_8;
