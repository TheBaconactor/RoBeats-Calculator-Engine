-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_23 = {
    ["DEFAULT_EQUIPPED_MIN_ID"] = 1,
    ["DEFAULT_EQUIPPED_MAX_ID"] = 12,
    ["get_owned_danceid_to_equipped_dict"] = function(_, p7) --[[ Name: get_owned_danceid_to_equipped_dict ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_1, (copy 3): v_u_5 ]]
        local v8 = v_u_4:new()
        for v9, v10 in v_u_1:singleton():key_itr() do
            if v10:is_dance_default_owned() then
                v8:add(v9, false)
            end;
        end;
        for v11 = 1, #p7.DanceOwned do
            v8:add(p7.DanceOwned[v11].ID, false)
        end;
        for v12 = 1, #p7.DanceEquipped do
            local l_ID_0 = p7.DanceEquipped[v12].ID
            if v8:contains(l_ID_0) then
                v8:add(l_ID_0, true)
            else
                v_u_5:warnf("PlayerBlobDance:get_owned_danceid_to_equipped_dict equipped but not owned(%s)", (tostring(l_ID_0)))
            end;
        end;
        return v8;
    end,
    ["set_danceid_equipped"] = function(_, p13, p14, p15) --[[ Name: set_danceid_equipped ]] --[[ Line: 97 ]]
        local v16 = -1
        for v17 = 1, #p13.DanceEquipped do
            if p13.DanceEquipped[v17].ID == p14 then
                v16 = v17
                break;
            end;
        end;
        if p15 then
            if v16 == -1 then
                p13.DanceEquipped[#p13.DanceEquipped + 1] = {
                    ["ID"] = p14
                }
                return;
            end;
        elseif v16 ~= -1 then
            table.remove(p13.DanceEquipped, v16)
        end;
    end,
    ["write_dance_equipped"] = function(_, p18, p19) --[[ Name: write_dance_equipped ]] --[[ Line: 117 ]]
        p18.DanceEquipped = {}
        for v20 = 1, #p19 do
            p18.DanceEquipped[#p18.DanceEquipped + 1] = {
                ["ID"] = p19[v20].ID
            }
        end;
    end,
    ["add_owned_danceid"] = function(_, p21, p22) --[[ Name: add_owned_danceid ]] --[[ Line: 124 ]]
        p21.DanceOwned[#p21.DanceOwned + 1] = {
            ["ID"] = p22
        }
    end
}
v_u_23.validate_playerblob = function(_, p24) --[[ Name: validate_playerblob ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    v_u_23:validate_playerblob_danceequipped_danceowned(p24.DanceEquipped, p24.DanceOwned)
end;
v_u_23.validate_playerblob_danceequipped_danceowned = function(_, p25, p26) --[[ Name: validate_playerblob_danceequipped_danceowned ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_23, (copy 4): v_u_2, (copy 5): v_u_4, (copy 6): v_u_3, (copy 7): v_u_5 ]]
    v_u_6:is_table(p25)
    v_u_6:is_table(p26)
    if #p25 == 0 then
        for v27, v28 in v_u_1:singleton():key_itr() do
            local v29 = v28:get_dance_type()
            if v_u_23.DEFAULT_EQUIPPED_MIN_ID <= v27 and (v27 <= v_u_23.DEFAULT_EQUIPPED_MAX_ID and (v28:is_dance_default_owned() and (v29 == v_u_2.OnMiss or (v29 == v_u_2.Standard or v29 == v_u_2.Combo)))) then
                p25[#p25 + 1] = {
                    ["ID"] = v27
                }
            end;
        end;
    end;
    local v_u_30 = v_u_4:new()
    for v31, v32 in v_u_1:singleton():key_itr() do
        if v32:is_dance_default_owned() then
            v_u_30:add(v31, true)
        end;
    end;
    v_u_3:new(p26):remove_if(function(p33) --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_30, (ref 3): v_u_5 ]]
        local l_ID_1 = p33.ID
        local v34 = false
        if v_u_1:singleton():contains_dance_for_id(l_ID_1) then
            v_u_30:add(l_ID_1, true)
            return v34;
        else
            v_u_5:warnf("PlayerBlobDance:validate_playerblob_danceequipped_danceowned dance_owned itr id(%s) not in DanceDatabase", (tostring(l_ID_1)))
            return true;
        end;
    end)
    v_u_3:new(p25):remove_if(function(p35) --[[ Line: 51 ]]
        --[[ Upvalues: (copy 1): v_u_30, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): v_u_2 ]]
        local l_ID_2 = p35.ID
        local v36
        if v_u_30:contains(l_ID_2) == true then
            v36 = false
        else
            v_u_5:warnf("PlayerBlobDance:validate_playerblob_danceequipped_danceowned dance_equipped id(%s) in equipped, not in owned_dance_ids", (tostring(l_ID_2)))
            v36 = true
        end;
        if v_u_1:singleton():contains_dance_for_id(l_ID_2) ~= true then
            v_u_5:warnf("PlayerBlobDance:validate_playerblob_danceequipped_danceowned dance_equipped id(%s) equipped, but not in DanceDatabase", (tostring(l_ID_2)))
            v36 = true
        end;
        if v_u_1:singleton():get_dance_type_for_id(l_ID_2) ~= v_u_2.Idle ~= true then
            v_u_5:warnf("PlayerBlobDance:validate_playerblob_danceequipped_danceowned dance_equipped id(%s) equipped, but is idle", (tostring(l_ID_2)))
            v36 = true
        end;
        return v36;
    end)
end;
v_u_23.is_dance_equipped = function(_, p37, p38) --[[ Name: is_dance_equipped ]] --[[ Line: 92 ]]
    --[[ Upvalues: (copy 1): v_u_23 ]]
    local v39 = v_u_23:get_owned_danceid_to_equipped_dict(p37)
    local v40 = v39:contains(p38)
    if v40 then
        v40 = v39:get(p38) == true
    end;
    return v40;
end;
return v_u_23;
