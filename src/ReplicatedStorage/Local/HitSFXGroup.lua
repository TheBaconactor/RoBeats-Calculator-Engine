-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:25 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
local v5 = {}
local v_u_6 = v2:new()
v5.new = function(_, p_u_7, p_u_8) --[[ Name: new ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_6 ]]
    local v9 = {}
    local v_u_10 = 1
    local v_u_11 = v_u_1:new()
    local v_u_12 = 0.15
    v9.cons = function(_) --[[ Name: cons ]] --[[ Line: 17 ]]
        --[[ Upvalues: (copy 1): p_u_8, (copy 2): v_u_11, (ref 3): v_u_3, (ref 4): v_u_12, (ref 5): v_u_4 ]]
        if p_u_8 == 0 then
            v_u_11:push_back(v_u_3.SFX_HITFXG_TAMB_1)
            v_u_11:push_back(v_u_3.SFX_HITFXG_TAMB_2)
            v_u_12 = 0.1
        elseif p_u_8 == 1 then
            v_u_11:push_back(v_u_3.SFX_HITFXG_INDHIHAT_1)
            v_u_11:push_back(v_u_3.SFX_HITFXG_INDHIHAT_2)
            v_u_11:push_back(v_u_3.SFX_HITFXG_INDHIHAT_3)
            v_u_12 = 0.25
        elseif p_u_8 == 2 then
            v_u_11:push_back(v_u_3.SFX_HITFXG_DRUM_1)
            v_u_11:push_back(v_u_3.SFX_HITFXG_DRUM_2)
            v_u_12 = 0.1
        elseif p_u_8 == 3 then
            v_u_11:push_back(v_u_3.SFX_HITFXG_CLAP_1)
            v_u_11:push_back(v_u_3.SFX_HITFXG_CLAP_2)
            v_u_12 = 0.1
        elseif p_u_8 == 4 then
            v_u_11:push_back(v_u_3.SFX_HITFXG_HIHAT_1)
            v_u_11:push_back(v_u_3.SFX_HITFXG_HIHAT_2)
            v_u_11:push_back(v_u_3.SFX_HITFXG_HIHAT_3)
            v_u_12 = 0.2
        elseif p_u_8 == 5 then
            v_u_11:push_back(v_u_3.SFX_HITFXG_JAZZHH_1)
            v_u_11:push_back(v_u_3.SFX_HITFXG_JAZZHH_2)
            v_u_11:push_back(v_u_3.SFX_HITFXG_JAZZHH_3)
            v_u_12 = 0.125
        else
            v_u_4:errf("invalid sfxg_id(%s)", (tostring(p_u_8)))
        end;
        v_u_12 = v_u_12 * 0.25
    end;
    v9.set_volume = function(_, p13) --[[ Name: set_volume ]] --[[ Line: 57 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        v_u_12 = p13
    end;
    v9.preload = function(_) --[[ Name: preload ]] --[[ Line: 61 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_8, (copy 3): v_u_11, (copy 4): p_u_7, (ref 5): v_u_12 ]]
        if v_u_6:contains(p_u_8) == false then
            for v14 = 1, v_u_11:count() do
                p_u_7._sfx_manager:preload(v_u_11:get(v14), 3, v_u_12)
            end;
            v_u_6:add(p_u_8, true)
        end;
    end;
    v9.play_alternating = function(_) --[[ Name: play_alternating ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): p_u_7, (copy 2): v_u_11, (ref 3): v_u_10, (ref 4): v_u_12 ]]
        p_u_7._sfx_manager:play_sfx(v_u_11:get(v_u_10), v_u_12)
        v_u_10 = v_u_10 + 1
        if v_u_10 > v_u_11:count() then
            v_u_10 = 1
        end;
    end;
    v9.play_first = function(_) --[[ Name: play_first ]] --[[ Line: 79 ]]
        --[[ Upvalues: (copy 1): p_u_7, (copy 2): v_u_11, (ref 3): v_u_12, (ref 4): v_u_10 ]]
        p_u_7._sfx_manager:play_sfx(v_u_11:get(1), v_u_12)
        v_u_10 = 2
        if v_u_10 > v_u_11:count() then
            v_u_10 = 1
        end;
    end;
    v9:cons()
    return v9;
end;
return v5;
