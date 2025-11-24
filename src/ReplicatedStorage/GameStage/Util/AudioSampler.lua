-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:09 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
return {
    ["new"] = function(_, p_u_3) --[[ Name: new ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v_u_4 = {}
        local v_u_5 = 1
        local v_u_6 = 0
        local v_u_7 = v_u_1:new()
        local function _() --[[ Name: cons ]] --[[ Line: 14 ]]
            --[[ Upvalues: (copy 1): v_u_4, (ref 2): v_u_5 ]]
            v_u_4:set_sample_count(v_u_5)
        end;
        v_u_4.set_sample_count = function(_, p8) --[[ Name: set_sample_count ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_7 ]]
            if p8 > 0 then
                v_u_5 = p8
                while v_u_5 < v_u_7:count() do
                    v_u_7:pop_front()
                end;
                while v_u_7:count() < v_u_5 do
                    v_u_7:push_back(0)
                end;
            end;
        end;
        v_u_4.get_samples = function(_) --[[ Name: get_samples ]] --[[ Line: 29 ]]
            --[[ Upvalues: (copy 1): v_u_7 ]]
            return v_u_7;
        end;
        v_u_4.update = function(_, p9) --[[ Name: update ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_6, (copy 3): v_u_7, (copy 4): p_u_3 ]]
            v_u_6 = v_u_6 + v_u_2:TimescaleToDeltaTime(p9)
            if v_u_6 > 0.05 then
                v_u_6 = v_u_6 - 0.05
                v_u_7:pop_front()
                v_u_7:push_back(p_u_3:es_gamelocal_get_audiomanager():get_bgm().PlaybackLoudness)
            end;
        end;
        v_u_4:set_sample_count(v_u_5)
        return v_u_4;
    end
};
