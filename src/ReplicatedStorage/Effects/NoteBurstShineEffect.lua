-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:23 PM
-- Cached decompilation

require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
return {
    ["new"] = function(_, p_u_4, p_u_5, p_u_6) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v7 = {
            ["Type"] = "NoteBurstShineEffect"
        }
        local v_u_8 = 0
        local v_u_9 = nil
        local v_u_10 = nil
        v7.cons = function(p11) --[[ Name: cons ]] --[[ Line: 16 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_4, (ref 3): v_u_1, (copy 4): p_u_5, (ref 5): v_u_10, (ref 6): v_u_3, (copy 7): p_u_6 ]]
            v_u_9 = p_u_4._object_pool:depool(p11.Type)
            if v_u_9 == nil then
                v_u_9 = game.ReplicatedStorage.ElementProtos.NoteBurstShineEffectProto:Clone()
            end;
            v_u_9.Name = v_u_1:gen_name(v_u_9.Name)
            v_u_9.Surface.Position = p_u_5
            v_u_10 = v_u_9.Surface.ParticleEmitter
            v_u_3:singleton():get_fevericon_for_id(p_u_4:get_game_note_skin_info():get_slot_fevericon_effect_from_setting(p_u_6)):apply_to_emitter(v_u_10)
            v_u_10.Size = NumberSequence.new({
                NumberSequenceKeypoint.new(0, 0),
                NumberSequenceKeypoint.new(0.04, 0.625),
                NumberSequenceKeypoint.new(0.075, 1.25),
                NumberSequenceKeypoint.new(0.1, 0.625),
                NumberSequenceKeypoint.new(0.4, 0),
                NumberSequenceKeypoint.new(1, 0)
            })
            v_u_10.Lifetime = NumberRange.new(0.8, 1.3)
            v_u_10.Speed = NumberRange.new(5, 10)
            v_u_10.SpreadAngle = Vector2.new(90, 90)
        end;
        v7.add_to_parent = function(_, p12, _) --[[ Name: add_to_parent ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9.Parent = p12
        end;
        v7.update = function(_, p13, _) --[[ Name: update ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_2, (ref 3): v_u_10 ]]
            v_u_8 = v_u_8 + v_u_2:SecondsToTick(0.55) * p13
            if v_u_8 < 0.4 then
                v_u_10.Enabled = true
            else
                v_u_10.Enabled = false
            end;
        end;
        v7.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8 >= 1;
        end;
        v7.do_remove = function(p14, _) --[[ Name: do_remove ]] --[[ Line: 56 ]]
            --[[ Upvalues: (copy 1): p_u_4, (ref 2): v_u_9 ]]
            p_u_4._object_pool:repool(p14.Type, v_u_9)
            p14._effect_obj = nil
        end;
        v7:cons()
        return v7;
    end
};
