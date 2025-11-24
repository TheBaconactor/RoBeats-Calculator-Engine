-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:24 PM
-- Cached decompilation

require(game.ReplicatedStorage.Effects.EffectSystem)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
return {
    ["CHARACTER_POSITION_OFFSET"] = Vector3.new(0, -2, 0),
    ["new"] = function(_, p_u_2, p_u_3, p_u_4) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v5 = {
            ["update"] = function(_, _, _) end
        }
        v5.get_game_slot = function(_) --[[ Name: get_game_slot ]] --[[ Line: 14 ]]
            --[[ Upvalues: (copy 1): p_u_4 ]]
            return p_u_4;
        end;
        local v_u_6 = nil
        local v_u_7 = nil
        local v_u_8 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_2, (ref 3): v_u_7, (ref 4): v_u_8, (ref 5): v_u_1, (copy 6): p_u_3, (copy 7): p_u_4 ]]
            v_u_6 = p_u_2:Clone()
            v_u_7 = v_u_6.PrimaryPart.ParticleEmitter
            v_u_8 = v_u_6.LightSurface.SurfaceLight
            v_u_7.Enabled = false
            v_u_8.Enabled = false
            v_u_1:singleton():get_fevericon_for_id(p_u_3:get_game_note_skin_info():get_slot_fevericon_effect_from_setting(p_u_4)):apply_to_emitter(v_u_7)
            v_u_7.Size = NumberSequence.new({
                NumberSequenceKeypoint.new(0, 0),
                NumberSequenceKeypoint.new(0.04, 0.625),
                NumberSequenceKeypoint.new(0.075, 1.25),
                NumberSequenceKeypoint.new(0.1, 0.625),
                NumberSequenceKeypoint.new(0.4, 0),
                NumberSequenceKeypoint.new(1, 0)
            })
            v_u_7.Lifetime = NumberRange.new(2, 2.3)
            v_u_7.Rate = 20
            v_u_7.Speed = NumberRange.new(5, 10)
            v_u_7.SpreadAngle = Vector2.new(0, 0)
        end;
        v5.get_cframe = function(_) --[[ Name: get_cframe ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            return v_u_6.PrimaryPart.CFrame;
        end;
        v5.set_cframe = function(p9, p10) --[[ Name: set_cframe ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            v_u_6:SetPrimaryPartCFrame(p10)
            return p9;
        end;
        v5.set_light_active = function(_, p11) --[[ Name: set_light_active ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8.Enabled = p11
        end;
        v5.set_emitter_active = function(_, p12) --[[ Name: set_emitter_active ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7.Enabled = p12
        end;
        v5.add_to_parent = function(_, p13, _) --[[ Name: add_to_parent ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            v_u_6.Parent = p13
        end;
        v5.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            v_u_6:Destroy()
        end;
        f_cons()
        return v5;
    end
};
